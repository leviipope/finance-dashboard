### Possible upgrades
- ✅ demo mode: so user doesnt have to upload a file
- ✅ convert welcome message in sidebar to a st.toast() instead
    - (and maybe even the failed to upload x rows st.warning() too)
- use st.spinner where there are big load times

---

### Main page
- ✅ Make editable dataframe functionable
    - ✅ make the amount column editable
- ✅ Filtering options:
    - ✅ filter by date
    - ✅ filter by type
    - ✅ filter by transaction type
- ✅ bug: null balance
- ✅ bug: hide application
- ✅ bug: categorization works in df, not mirrored in csv
- implement categories 😭 
    - single transaction categoryizing feature
    - ✅ bug: when adding a completly new bank statement (with no categories.json and main_dataframe.csv), pressing apply amounts to an error

### Credits page
- ✅ monthly spending metrics
    - ✅ spending for specific month metric
- ✅ only include data that isnt hide=True
- ✅ date filter
- ✅ total spending with color gradient
- ✅ checkbox: display the credit dataframe
- ✅ spending over time
    - ✅ options: individual, daily, weekly
        - ✅ weekly: format amount value on bar
    - ✅ spending add-up over time
    - ✅ highlight unusual spikes
- ✅ list of biggest transactions in a month (top 10/15)
- ✅ daily spend heatmap
    - ✅ format hover data on all graphs like on this one
- ✅ balance over time
    - ✅ at each datapoint (when hovering) show deatils value

### Debits page
- ✅ savings account balance over time
- ✅ last months income as metric
- ✅ how much of your monthly income did you save?