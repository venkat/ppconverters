# Portfolio Performance CSV Converters

This project provides a collection of Python scripts to convert CSV files from various financial institutions into a generic format suitable for importing into [Portfolio Performance](https://www.portfolio-performance.info/en/), a powerful open-source tool for tracking your investments.

## Supported Institutions

These scripts are designed to work with transaction history CSVs downloaded from the following institutions and account types:

*   **Morgan Stanley**
    * Stock Unit (RSU) Plan Accounts. 
   
    Source: Activity Report from http://atwork.morganstanley.com/ (2 CSV files in the report - Releases report, Withdrawals report downloaded from Activity > Reports > Activity Report with Output Format CSV)

*   **Vanguard**
    *   401(k) & IRA Accounts
    *   Brokerage Accounts

    Source: CSV file downloaded from Vanguard's Download Center.
*   **Fidelity**
    *   401(k) & IRA Accounts

    Source: CSV downloaded from "Activity & Orders" tab on the Fidelity website.

## Usage

Each script is a command-line tool that reads an input CSV file, processes it, and prints the converted data to standard output. You can then redirect this output to a new CSV file.

**General Command:**

```bash
python <converter_script.py> <input_file.csv> > <output_file.csv>
```

**Example:**

To convert a Vanguard 401(k) transaction file, you would run:

```bash
python vanguard_401k_IRA_converter.py vanguard_transactions.csv > vanguard_pp_import.csv
```

## Output Format

The scripts generate a standardized 5-column CSV file with the following headers, ready for import into Portfolio Performance:

*   `Date`
*   `Investment`
*   `Transaction Type`
*   `Shares`
*   `Amount`

This format ensures that transactions like buys, sells, dividends, and fees are correctly recognized by Portfolio Performance.

The output CSV can contain several other columns carried over from the input. Map the right columns during the CSV import phase of Portfolio Performance or try out one of the import configurations in the `import_config` folder.
