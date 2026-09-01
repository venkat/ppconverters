# This script converts a Morgan Stanley GSU Releases or Withdrawals Report CSV file 
# into a format suitable for portfolio performance tracking software.
#
# It automatically detects the report type based on the header and applies the correct rules.
#
# To run this script from the command line:
# python3 morgan_stanley_gsu_converter.py "path/to/your/input_file.csv" > "path/to/your/output_file.csv"

import csv
import sys
import os

# Transaction types the Portfolio Performance import configurations in import_config/
# can map. Anything else in the 'Type' column makes PP fail with "Unable to parse value",
# so every such row gets a warning on stderr.
PP_IMPORT_TYPES = {
    'Buy', 'Sell', 'Dividend', 'Deposit', 'Removal', 'Interest', 'Interest Charge',
    'Fees', 'Fees Refund', 'Taxes', 'Tax Refund', 'Transfer (Inbound)', 'Transfer (Outbound)',
}


def warn_if_unmapped(type_value, row):
    """Print a stderr warning when PP will not be able to import this row's type."""
    if type_value not in PP_IMPORT_TYPES:
        print(f"WARNING: transaction type '{type_value}' has no Portfolio Performance mapping and must be "
              f"handled manually in PP -> {row}", file=sys.stderr)

def process_releases_report(header, reader, writer):
    """
    Processes a GSU Releases report by applying its specific transformation rules.
    """
    # --- Find indices of columns for the Releases report ---
    price_index = header.index('Price')
    type_index = header.index('Type')
    order_number_index = header.index('Order Number')
    net_share_proceeds_index = header.index('Net Share Proceeds')

    # --- Modify header for the Releases report output ---
    # Add 'Symbol' and 'Value' columns to the header.
    header.insert(order_number_index + 1, 'Symbol')
    header.insert(net_share_proceeds_index + 2, 'Value')
    writer.writerow(header)

    # --- Process each data row ---
    for row in reader:
        # Rule: Remove '$' from 'Price' for calculation.
        price_str = row[price_index].replace('$', '')
        try:
            price_float = float(price_str)
        except ValueError:
            print(f"Warning: Could not parse price in Releases row: {row}. Skipping.", file=sys.stderr)
            continue
        
        # Update the row with the cleaned price string.
        row[price_index] = price_str

        # Rule: Change 'Type' from 'Release' to 'Buy'.
        if row[type_index] == 'Release':
            row[type_index] = 'Buy'
        warn_if_unmapped(row[type_index], row)

        # Rule: Calculate the 'Value' of the released shares.
        try:
            net_shares_float = float(row[net_share_proceeds_index])
        except ValueError:
            print(f"Warning: Could not parse Net Share Proceeds in Releases row: {row}. Skipping.", file=sys.stderr)
            continue
        
        value = price_float * net_shares_float
        
        # Rule: Insert the stock symbol ('GOOG').
        row.insert(order_number_index + 1, 'GOOG')

        # Rule: Insert the calculated 'Value', formatted to two decimal places.
        row.insert(net_share_proceeds_index + 2, f"{value:.2f}")

        writer.writerow(row)

def process_withdrawals_report(header, reader, writer):
    """
    Processes a Withdrawals report by applying its specific transformation rules.
    """
    # --- Find indices of columns for the Withdrawals report ---
    type_index = header.index('Type')
    order_number_index = header.index('Order Number')
    plan_index = header.index('Plan')
    quantity_index = header.index('Quantity')
    net_amount_index = header.index('Net Amount')

    # --- Modify header for the Withdrawals report output ---
    # Add the 'Symbol' column to the header.
    header.insert(order_number_index + 1, 'Symbol')
    writer.writerow(header)

    # --- Process each data row ---
    for row in reader:
        # Skip the common footer line found in these reports.
        if row and row[0].startswith('Please note that'):
            continue

        # Rule: Plan = 'Cash' rows are NOT dividends. Morgan Stanley books a withdrawal of
        # the cash balance (accumulated dividends) as a "sale" of Cash at $1.00; the same
        # order number shows up in the Withdrawal Wire Report as a wire out. In PP that is
        # a Removal from the deposit account: no shares and no security attached.
        is_cash_withdrawal = row[plan_index] == 'Cash'
        if is_cash_withdrawal:
            row[type_index] = 'Removal'
            row[quantity_index] = ''
        elif row[type_index] == 'Sale':
            # Rule: Change 'Type' from "Sale" to "Sell" for stock sales.
            row[type_index] = 'Sell'
        warn_if_unmapped(row[type_index], row)

        # Rule: Remove the "-" sign from the 'Quantity' value.
        row[quantity_index] = row[quantity_index].replace('-', '')

        # Rule: Format 'Net Amount' to remove "$" and "," separators.
        row[net_amount_index] = row[net_amount_index].replace('$', '').replace(',', '')

        # Rule: Add the stock symbol ('GOOG'); a cash withdrawal gets no symbol so PP does
        # not attach a security to the Removal.
        row.insert(order_number_index + 1, '' if is_cash_withdrawal else 'GOOG')

        writer.writerow(row)

def process_morgan_stanley_report(input_file_path):
    """
    Opens a Morgan Stanley report, determines its type by inspecting the header,
    and calls the appropriate processing function.
    """
    try:
        with open(input_file_path, 'r', newline='') as infile:
            reader = csv.reader(infile)
            writer = csv.writer(sys.stdout)

            header = next(reader)

            # --- Determine Report Type by checking for unique column names ---
            if 'Vest Date' in header:
                # This is a "Releases" report.
                process_releases_report(header, reader, writer)
            elif 'Execution Date' in header:
                # This is a "Withdrawals" report.
                process_withdrawals_report(header, reader, writer)
            else:
                # If the report type is unknown, print an error.
                print("Error: Unknown report type. Header does not contain 'Vest Date' or 'Execution Date'.", file=sys.stderr)
                sys.exit(1)

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_file_path}'", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: A required column was not found in the CSV header. Details: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    # This block runs when the script is executed from the command line.
    if len(sys.argv) != 2:
        print(f"Usage: python3 {os.path.basename(__file__)} <input_file.csv>", file=sys.stderr)
        sys.exit(1)

    input_csv_path = sys.argv[1]
    
    # Call the main processing function with the provided file path.
    process_morgan_stanley_report(input_csv_path)