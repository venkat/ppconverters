# Import necessary libraries for CSV handling, in-memory file operations, system arguments, and OS-level operations.
import csv
import io
import sys
import os

# Transaction types that the Portfolio Performance import configurations in
# import_config/ know how to map. Any other value in the 'Type' column makes PP
# fail with "Unable to parse value ...", so a warning is printed on stderr for it.
PP_IMPORT_TYPES = {
    'Buy', 'Sell', 'Dividend', 'Deposit', 'Removal', 'Interest', 'Interest Charge',
    'Fees', 'Fees Refund', 'Taxes', 'Tax Refund', 'Transfer (Inbound)', 'Transfer (Outbound)',
}


def to_float(value):
    """Parse a numeric CSV cell; blanks or junk count as 0."""
    try:
        return float(str(value).replace('$', '').replace(',', '').strip() or 0)
    except ValueError:
        return 0.0

def convert_vanguard_401k_csv(input_file_path):
    """
    Parses a Vanguard 401K or Roth IRA CSV file, transforms it, and returns the result as a string.
    """
    # Use an in-memory StringIO object to build the output CSV. This is more efficient
    # than writing to a file on disk, as it avoids intermediate I/O operations.
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')

    with open(input_file_path, 'r', newline='') as infile:
        # Vanguard CSVs often have informational text at the beginning. We need to
        # find the actual start of the transaction data by looking for the header row.
        header = None
        for line in infile:
            if line.strip().startswith('Account Number,Trade Date'):
                # This is the header row, process it and then break to the csv reader
                # Once the header is found, parse it into a list of column names.
                header = [h.strip() for h in line.strip().split(',')]
                break
        
        if not header:
            return "" # No header found

        # Determine file type and set column names
        is_401k = 'Dollar Amount' in header
        is_roth = 'Principal Amount' in header

        if is_401k:
            amount_col_name = 'Dollar Amount'
            shares_col_name = 'Transaction Shares'
        elif is_roth:
            amount_col_name = 'Principal Amount'
            shares_col_name = 'Shares'
        else:
            raise ValueError("Unsupported CSV format: missing amount column ('Dollar Amount' or 'Principal Amount')")

        # Column positions in the ORIGINAL input layout. Each data row is still in
        # that layout until 'Type' is inserted into it further down, so every check
        # made before that insert must use these indices. (Using the modified header's
        # indices there is off by one for every column after 'Transaction Description':
        # it read the dollar amount where it meant to read the share count.)
        src_shares_index = header.index(shares_col_name)
        src_price_index = header.index('Share Price')
        src_amount_index = header.index(amount_col_name)

        # Transformation Rule: A new 'Type' column is needed for easier data processing.
        # We find the index of 'Transaction Description' to insert 'Type' right after it.
        desc_index = header.index('Transaction Description')
        header.insert(desc_index + 1, 'Type')
        # Column positions in the OUTPUT layout (after 'Type' has been inserted).
        out_shares_index = header.index(shares_col_name)
        unmapped_rows = 0
        # Write the new, modified header to our in-memory output.
        writer.writerow(header)
        
        # The rest of the file is the transaction data
        # Continue reading from the file where the header search left off.
        reader = csv.reader(infile)
        for row in reader:
            if not row: break #Stop processing on encountering the first empty row, which signifies the end of the transaction block

            # Get transaction description directly from the row
            # To apply rules, we first need to identify the transaction type from its description.
            transaction_description = row[header.index('Transaction Description')]

            # Filtering Rules based on file type
            if is_401k:
                if 'Source to Source/Fund to Fund Transfer' in transaction_description:
                    continue
                # Vanguard books plan-level adjustments as 'Miscellaneous Credits/Adjustment',
                # 'Miscellaneous Credit to Forfeiture Account', etc. Ones with zero shares are
                # pure dollar adjustments that do not change the position, so skip them.
                if transaction_description.startswith('Miscellaneous Credit') and to_float(row[src_shares_index]) == 0:
                    continue
            elif is_roth:
                if 'Sweep' in transaction_description:
                    continue

            # Generic Filtering Rules
            if transaction_description == 'Fee' and not row[src_price_index].strip():
                continue

            # Transformation Rule: Create the value for the new 'Type' column.
            type_col = transaction_description

            # Type mapping based on file type
            if is_401k:
                if transaction_description.startswith('Miscellaneous Credit'):
                    # The sign of the SHARE change decides: shares added to the account
                    # (e.g. a credit from the plan's forfeiture account) is a Buy, shares
                    # taken away is a Sell. Zero-share rows were skipped above.
                    shares_value = to_float(row[src_shares_index])
                    if shares_value < 0:
                        type_col = 'Sell'
                    elif shares_value > 0:
                        type_col = 'Buy'

                if type_col == 'Plan Contribution':
                    type_col = 'Buy'
                elif type_col == 'Fee':
                    # Vanguard pays plan fees by redeeming shares. A plain 'Fees' entry in PP
                    # ignores the share count, so the position drifts up by ~0.008 shares per
                    # fee. Model it exactly instead: a Sell of the redeemed shares here, plus a
                    # matching 'Fees' row (written further down) so the fee still shows as a
                    # cost. The two cancel in the cash account.
                    type_col = 'Sell'
                elif type_col == 'Fund to Fund Out':
                    type_col = 'Sell'
                elif type_col == 'Fund to Fund In':
                    type_col = 'Buy'
            elif is_roth:
                if type_col == 'Dividend Reinvestment':
                    type_col = 'Buy'
                elif type_col == 'Dividend Received':
                    type_col = 'Dividend'
                elif type_col == 'Rollover Conversion':
                    type_col = 'Deposit'

            if type_col not in PP_IMPORT_TYPES:
                unmapped_rows += 1
                print(f"WARNING: transaction type '{type_col}' has no Portfolio Performance mapping and must be "
                      f"handled manually in PP -> {row[header.index('Trade Date')]} '{transaction_description}' "
                      f"shares={row[src_shares_index]} amount={row[src_amount_index]}",
                      file=sys.stderr)

            # Insert the new 'Type' value into the row
            row.insert(desc_index + 1, type_col)

            # Transformation Rule: Standardize investment fund names for consistency.
            investment_name_index = header.index('Investment Name')
            investment_name = row[investment_name_index]
            if investment_name == 'Target Retire 2050 Tr':
                row[investment_name_index] = 'Vanguard Target Retirement 2050 Trust'
            elif investment_name == 'Tgt Retire 2070 Trust':
                row[investment_name_index] = 'Vanguard Target Retirement 2070 Trust'

            # Data Cleaning Rule: Remove dollar signs ('$') and negative signs from monetary values
            price_index = header.index('Share Price')
            amount_index = header.index(amount_col_name)
            
            if price_index < len(row) and row[price_index]:
                row[price_index] = row[price_index].replace('$', '')

            if amount_index < len(row) and row[amount_index]:
                row[amount_index] = row[amount_index].replace('$', '')
                if is_roth or is_401k:
                    row[amount_index] = row[amount_index].replace('-', '')
            if is_401k and out_shares_index < len(row) and row[out_shares_index]:
                row[out_shares_index] = row[out_shares_index].replace('-', '')

            if is_roth:
                if 'Net Amount' in header:
                    net_amount_index = header.index('Net Amount')
                    if net_amount_index < len(row) and row[net_amount_index]:
                        row[net_amount_index] = row[net_amount_index].replace('-', '')

            # Write the cleaned and transformed row to the in-memory output.
            writer.writerow(row)

            # Second half of the fee handling (see above): the 'Fees' entry for the same
            # amount. Shares are blanked because PP ignores them on a fee anyway.
            if is_401k and transaction_description == 'Fee':
                fee_row = list(row)
                fee_row[desc_index + 1] = 'Fees'
                fee_row[out_shares_index] = ''
                writer.writerow(fee_row)

    if unmapped_rows:
        print(f"WARNING: {unmapped_rows} row(s) have a transaction type Portfolio Performance cannot import "
              f"(see above).", file=sys.stderr)

    # Return the complete CSV data as a single string.
    return output.getvalue()

# This block ensures the code runs only when the script is executed directly.
if __name__ == '__main__':
    # Check if the user provided an input file path as a command-line argument.
    if len(sys.argv) < 2:
        print('Usage: python3 vanguard_401k_converter.py <input_csv_file_path>')
        sys.exit(1)

    input_csv = sys.argv[1]
    
    # Check if the specified input file actually exists before trying to process it.
    if not os.path.exists(input_csv):
        print(f'Error: Input file not found at \'{input_csv}\'')
        sys.exit(1)

    # Call the main conversion function to get the transformed data.
    transformed_content = convert_vanguard_401k_csv(input_csv)
    # Print the final result to standard output, which can be redirected to a file.
    print(transformed_content, end='')
