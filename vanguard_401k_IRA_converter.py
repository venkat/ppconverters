# Import necessary libraries for CSV handling, in-memory file operations, system arguments, and OS-level operations.
import csv
import io
import sys
import os

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

        # Transformation Rule: A new 'Type' column is needed for easier data processing.
        # We find the index of 'Transaction Description' to insert 'Type' right after it.
        desc_index = header.index('Transaction Description')
        header.insert(desc_index + 1, 'Type')
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
                if transaction_description.startswith('Miscellaneous Credits') and float(row[header.index(shares_col_name)]) == 0:
                    continue
            elif is_roth:
                if 'Sweep' in transaction_description:
                    continue

            # Generic Filtering Rules
            if transaction_description == 'Fee' and not row[header.index('Share Price')].strip():
                continue

            # Transformation Rule: Create the value for the new 'Type' column.
            type_col = transaction_description

            # Type mapping based on file type
            if is_401k:
                if transaction_description.startswith('Miscellaneous Credits'):
                    try:
                        shares_value = float(row[header.index(shares_col_name)])
                        if shares_value < 0:
                            type_col = 'Sell'
                        elif shares_value > 0:
                            type_col = 'Buy'
                    except (ValueError, IndexError):
                        # If for some reason shares aren't a number, leave the type as is.
                        pass
                
                if type_col == 'Plan Contribution':
                    type_col = 'Buy'
                elif type_col == 'Fee':
                    type_col = 'Fees'
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
                    type_col = 'Buy'

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
                if is_roth:
                    row[amount_index] = row[amount_index].replace('-', '')

            if is_roth:
                if 'Net Amount' in header:
                    net_amount_index = header.index('Net Amount')
                    if net_amount_index < len(row) and row[net_amount_index]:
                        row[net_amount_index] = row[net_amount_index].replace('-', '')

            # Write the cleaned and transformed row to the in-memory output.
            writer.writerow(row)

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
    print(transformed_content)
