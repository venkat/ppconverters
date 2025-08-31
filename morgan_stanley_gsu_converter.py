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

        # Rule: Change 'Type' from "Sale" to "Sell".
        if row[type_index] == 'Sale':
            row[type_index] = 'Sell'
        
        # Rule: Remove the "-" sign from the 'Quantity' value.
        row[quantity_index] = row[quantity_index].replace('-', '')

        # Rule: Format 'Net Amount' to remove "$" and "," separators.
        row[net_amount_index] = row[net_amount_index].replace('$', '').replace(',', '')

        # Rule: Add the stock symbol ('GOOG').
        row.insert(order_number_index + 1, 'GOOG')
        
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