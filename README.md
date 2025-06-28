# Finance Dashboard

A personal finance dashboard built with Streamlit that tracks spending, categorizes transactions, and provides insights into financial habits.

## Features
- 🔐 User authentication with password encryption
- 📊 Interactive spending analytics and visualizations
- 🏷️ Automatic transaction categorization
- 💾 Cloud data storage via private GitHub repository
- 📱 Mobile-friendly responsive design

## Demo
🚀 **Live App**: [Your Streamlit Cloud URL will be here]

## Local Development
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml` with your GitHub credentials
4. Run: `streamlit run app.py`

## Deployment
This app is deployed on Streamlit Cloud with data stored securely in a private GitHub repository.

### PROD Status
- ✅ login/registration for users
- ✅ password encryption
- ✅ changes committed to private GitHub repository
- ✅ log file functionality
- 🚧 user data deletion option

// ...rest of existing content...

# Questlog
### PROD
- ✅ login/registration for users
- ✅ password encyption
- ✅ changes in the files should be commited to a private github repository when button is clicked
    - ✅ everytime a change is made should there be a commit
- log file
- user data deletion option


plans/help:
https://chatgpt.com/share/685c1383-10ec-8000-b168-0757a011a0da
https://g.co/gemini/share/dd8f704e4076

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
- ✅how much of your monthly income did you save?
