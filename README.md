# Questlog

### Main page
- Make editable dataframe functionable ✅
- Filtering options:
    - filter by date ✅
    - filter by type ✅
    - filter by transaction type ✅
- bug: null balance ✅
- bug: hide application ✅
- bug: categorization works in df, not mirrored in csv ✅
- implement categories 😭 ✅
    - single transaction categoryizing feature
    - bug: after pressing apply, you need to manually reload the page for the categorization
    - bug: when adding a complete new bank statement (with no categories.json and main_dataframe.csv), pressing apply amounts to an error

### Credits page
- only include data that isnt hide=True ✅
- date filter ✅
- total spending with color gradient 🚧
    - check for a color graident picker API or smth
    - check for a better solution then st.markdown
- checkbox: display the credit dataframe ✅
- spending over time 🚧
    - options: individual, daily, weekly 🚧
    - when individual is select, make two graphs, the right one adds up transactions over time
    - highlight unusual spikes
- list of biggest transactions in a month (top 10/15)
- daily spend heatmap?
- balance over time 🚧 (its still missing something)

### Debits page
- savings account balance over time
- how much % of income did you invest each month?
- Migrate the savings account balance tracker from the Notes app to here.
