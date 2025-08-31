import csv
import sys

def process_fidelity_csv(input_file_path):
    """
    Reads a Fidelity 401K or IRA CSV file, applies conversion rules,
    and prints the result to standard output in a standardized 5-column CSV format.
    It handles two different Fidelity CSV formats: a 5-column 401k format and a 13-column IRA format.
    """
    try:
        # Open with 'utf-8-sig' to handle the BOM (Byte Order Mark)
        with open(input_file_path, 'r', encoding='utf-8-sig') as infile:
            # Find header and data lines, skipping any empty lines at the top
            lines = []
            header_found = False
            for line in infile:
                stripped_line = line.strip()
                if not stripped_line:
                    if not header_found:
                        continue # Skip blank lines at the beginning
                    else:
                        break # Stop at first blank line after data
                
                if not header_found:
                    if stripped_line.startswith('Date,') or stripped_line.startswith('Run Date,'):
                        header_found = True
                    else:
                        # If we haven't found a header and the line is not a header, skip it.
                        # This handles cases with extra text before the header.
                        continue
                
                lines.append(line)

            if not lines:
                print("Error: No data found in file.", file=sys.stderr)
                sys.exit(1)

            # Process the captured lines
            reader = csv.reader(lines)
            writer = csv.writer(sys.stdout)

            # Read the header to determine the file format
            header = next(reader)

            # Write a standardized header for the output
            writer.writerow(['Date', 'Investment', 'Transaction Type', 'Shares', 'Amount'])

            # Process based on detected format from header
            if header[0] == 'Date' and len(header) == 5:
                # 401k format processing
                for row in reader:
                    if len(row) != 5:
                        continue

                    date, investment, trans_type, shares, amount = row

                    # Rule: Change investment name
                    if investment == "VANG TARGET RET 2070":
                        investment = "VSVNX"

                    # Rule: Delete any rows with type “Change in market value”
                    if trans_type == "Change in Market Value":
                        continue

                    # Rule: Delete are “transfers” type rows with 0 amounts
                    if trans_type in ("Transfers", "Transfer") and amount and float(amount) == 0.0:
                        continue

                    # Rule: Change transaction type “Contributions” to “Buy”
                    if trans_type == "Contributions":
                        trans_type = "Buy"

                    # Rule: Change “Exchange In” type to “Buy”
                    if trans_type == "Exchange In":
                        trans_type = "Buy"

                    # Rule: Change “Exchange Out” type to “Sell”
                    if trans_type == "Exchange Out":
                        trans_type = "Sell"
                    
                    # Rule: Change “RECORDKEEPING FEE” type to “Fees”
                    if trans_type == "RECORDKEEPING FEE":
                        trans_type = "Fees"

                    # Rule: Strip any negative signs for shares/unit and amount columns.
                    shares = shares.lstrip('-')
                    amount = amount.lstrip('-')

                    writer.writerow([date, investment, trans_type, shares, amount])

            elif header[0] == 'Run Date' and len(header) == 13:
                # Roth IRA format processing
                for row in reader:
                    if len(row) != 13:
                        continue

                    date = row[0]
                    action = row[1]
                    investment = row[2]  # Symbol
                    shares = row[5]      # Quantity
                    amount = row[10]     # Amount ($)

                    trans_type = action # Default to action
                    if "REINVESTMENT" in action:
                        trans_type = "Buy"
                    elif "DIVIDEND RECEIVED" in action:
                        trans_type = "Dividend"
                    
                    # For this format, we don't need to change investment name as Symbol is good.
                    # We can add more rules here if needed for other actions.

                    # Rule: Strip any negative signs for shares/unit and amount columns.
                    shares = shares.lstrip('-')
                    amount = amount.lstrip('-')

                    writer.writerow([date, investment, trans_type, shares, amount])
            else:
                print(f"Error: Unsupported CSV format. Header found: {header}", file=sys.stderr)
                sys.exit(1)

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # This script is designed to be used as a command-line tool.
    # Example usage:
    # python fidelity_401k_converter.py /path/to/your/History_for_Account.csv > output.csv
    if len(sys.argv) != 2:
        print("Usage: python fidelity_401k_converter.py <input_csv_file>", file=sys.stderr)
        sys.exit(1)

    input_csv_file = sys.argv[1]
    process_fidelity_csv(input_csv_file)