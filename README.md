# Finance Dashboard

A personal finance dashboard built with Streamlit that tracks spending, categorizes transactions, and provides insights into financial habits. Currently only works with Revolut.

## Features
- 🔐 User authentication with password encryption
- 📊 Interactive spending analytics and visualizations
- 🏷️ Automatic transaction categorization
- 💾 Cloud data storage via private GitHub repository
- 📱 Mobile-friendly responsive design

## Demo
🚀 **Live App**: https://revolut-data-analysis.streamlit.app

## Deployment
This app is deployed on Streamlit Cloud with data stored securely in a private GitHub repository.

### PROD Status
- ✅ login/registration for users
- ✅ password encryption
- ✅ changes committed to private GitHub repository
- ✅ change password feature
- ✅ user data encryption
- 🚧 user data deletion option


# Questlog
### Known bugs
- currency is HUF everwhere -> make it universal
- convert welcome message in sidebar to a st.toast() instead (and maybe even the failed to upload x rows st.warning() too)

### PROD
- ✅ login/registration for users
- ✅ password encyption
- ✅ changes in the files should be commited to a private github repository when button is clicked
    - ✅ everytime a change is made should there be a commit
- log file
- user data deletion option
- user data encyption

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
    - spending for specific month metric
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
- 🚧 balance over time (its still missing something)
    - ✅ at each datapoint (when hovering) show deatils value

### Debits page
- ✅ savings account balance over time
- ✅ last months income as metric
- ✅ how much of your monthly income did you save?

### 🚧 How to use / About / Feedback / Contact page
