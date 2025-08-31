# Import necessary libraries for CSV handling and system operations.
import csv
import sys

# This function standardizes the transaction type string based on a set of rules.
# It checks if a transaction type starts with a known prefix and replaces it with a standard term.
# This helps in normalizing varied but similar transaction descriptions from the input file.
def apply_conversion_rules(transaction_type, rules):
    # Standardize by converting to lowercase and removing leading/trailing whitespace for consistent matching.
    lower_transaction_type = transaction_type.strip().lower()
    # Iterate through the defined conversion rules.
    for prefix, replacement in rules.items():
        # If the transaction type from the file matches a rule's prefix...
        if lower_transaction_type.startswith(prefix):
            # ...return the standardized transaction type.
            return replacement
    # If no rule matches, return the original transaction type.
    return transaction_type

# This is the main function to process the Vanguard brokerage CSV file.
# It reads the file, identifies the transaction data section, and applies specific
# formatting and conversion rules to each transaction row.
def process_vanguard_csv(input_file, rules):
    # Open the input CSV file for reading.
    with open(input_file, 'r', newline='') as infile:
        # Read all lines into a list for pre-processing.
        lines = infile.readlines()

    # The Vanguard CSV contains multiple sections (e.g., holdings, transactions).
    # We need to find the start of the actual transaction history, which is identified
    # by its specific header row.
    start_index = -1
    for i, line in enumerate(lines):
        # This header is the unique marker for the beginning of the transaction data.
        if 'Account Number,Trade Date,Settlement Date' in line:
            start_index = i
            break
    
    # If the transaction header is not found, the file may be in an unexpected format.
    if start_index == -1:
        print("Brokerage transaction data not found", file=sys.stderr)
        return

    # Extract the header line and parse it to get a list of column names.
    header_line = lines[start_index].strip()
    header = next(csv.reader([header_line]))
    
    # To make the script robust against changes in column order, we find the index
    # of the columns we need to modify.
    transaction_type_index = header.index('Transaction Type') if 'Transaction Type' in header else -1
    principal_amount_index = header.index('Principal Amount') if 'Principal Amount' in header else -1
    shares_index = header.index('Shares') if 'Shares' in header else -1

    # Print the header for the output. The output will be a valid CSV.
    print(header_line)

    # Process each line of transaction data, starting from the line after the header.
    for i in range(start_index + 1, len(lines)):
        line = lines[i].strip()
        # Stop processing if we hit an empty line or a new section header,
        # which indicates the end of the transaction data.
        if not line or line.startswith('Account Number,'):
            break

        try:
            # Parse the current line as a CSV row.
            row = next(csv.reader([line]))
        except StopIteration:
            # Skip any lines that are empty or fail to parse.
            continue
        
        # Check if the 'Transaction Type' column exists and the row is long enough.
        if transaction_type_index != -1 and len(row) > transaction_type_index:
            original_transaction_type = row[transaction_type_index].strip().lower()

            # Specific rule for 'sweep' transactions into/out of the settlement fund.
            # These are essentially buys/sells of the money market fund.
            if original_transaction_type.startswith('sweep in') or original_transaction_type.startswith('sweep out'):
                # For sweeps, the 'Shares' count should equal the 'Principal Amount'
                # because the price is always $1.00.
                if principal_amount_index != -1 and len(row) > principal_amount_index:
                    principal_amount = row[principal_amount_index]
                    # Ensure the principal amount is positive for consistency.
                    positive_principal = principal_amount[1:] if principal_amount.startswith('-') else principal_amount
                    row[principal_amount_index] = positive_principal
                    # Set the shares to be the same as the principal amount.
                    if shares_index != -1 and len(row) > shares_index:
                        row[shares_index] = positive_principal
            
            # Specific rule for 'reinvestment' transactions.
            elif original_transaction_type.startswith('reinvestment'):
                # The input file often lists the principal for reinvestments as negative.
                # We convert it to a positive value for the output format.
                if principal_amount_index != -1 and len(row) > principal_amount_index:
                    principal_amount = row[principal_amount_index]
                    if principal_amount.startswith('-'):
                        row[principal_amount_index] = principal_amount[1:]

            # Apply the general conversion rules to standardize the transaction type.
            row[transaction_type_index] = apply_conversion_rules(row[transaction_type_index], rules)
        
        # Print the processed row as a comma-separated string to standard output.
        print(','.join(row))

# This block executes when the script is run directly from the command line.
if __name__ == '__main__':
    # Ensure the user has provided the input file as a command-line argument.
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <input_file>", file=sys.stderr)
        sys.exit(1)
    
    # Define the mapping from Vanguard's transaction types to standardized types.
    # These rules are designed to create a generic, import-friendly CSV format.
    conversion_rules = {
        'capital gain': 'Interest',
        'reinvestment': 'Buy',
        'sweep in': 'Buy',
        'sweep out': 'Sell',
        'corp action (redemption)': 'Sell',
        'corp action (merger)': 'Sell',
        'wire in': 'Deposit',
        'funds received': 'Deposit',
        'sell (exchange)': 'Sell',
        'buy (exchange)': 'Buy',
        'conversion (incoming)': 'Deposit',
        'transfer (incoming)': 'Deposit',
        'transfer (outgoing)': 'Removal',
        'withdrawal': 'Removal'
    }
    
    # Get the input filename from the command-line arguments.
    input_filename = sys.argv[1]
    # Call the main processing function with the filename and conversion rules.
    process_vanguard_csv(input_filename, conversion_rules)
