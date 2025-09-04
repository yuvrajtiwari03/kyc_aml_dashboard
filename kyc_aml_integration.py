
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------
# Step 1: Load CSV files
# ---------------------------
kyc_df = pd.read_csv('kyc_final_report.csv')
transactions_df = pd.read_csv('transactions.csv')
suspicious_df = pd.read_csv('suspicious_transactions.csv')

# ---------------------------
# Step 2: Clean column names
# ---------------------------
kyc_df.columns = kyc_df.columns.str.strip().str.lower()
transactions_df.columns = transactions_df.columns.str.strip().str.lower()
suspicious_df.columns = suspicious_df.columns.str.strip().str.lower()

# ---------------------------
# Step 3: Clean CustomerID and remove 'CUST' prefix
# ---------------------------
kyc_df['customerid'] = kyc_df['customerid'].astype(str).str.extract('(\d+)')[0]
transactions_df['customerid'] = transactions_df['customerid'].astype(str).str.extract('(\d+)')[0]
suspicious_df['customerid'] = suspicious_df['customerid'].astype(str).str.extract('(\d+)')[0]

# ---------------------------
# Step 4: Flag suspicious customers
# ---------------------------
suspicious_customers = suspicious_df['customerid'].unique()
kyc_df['is_suspicious'] = kyc_df['customerid'].isin(suspicious_customers).map({True:'Yes', False:'No'})

# ---------------------------
# Step 5: Aggregate transactions
# ---------------------------
agg_txn = transactions_df.groupby('customerid').agg(
    total_amount=('transaction_amount', 'sum'),
    num_transactions=('transaction_amount', 'count')
).reset_index()

kyc_df = kyc_df.merge(agg_txn, on='customerid', how='left')
kyc_df['total_amount'] = kyc_df['total_amount'].fillna(0)
kyc_df['num_transactions'] = kyc_df['num_transactions'].fillna(0).astype(int)

# ---------------------------
# Step 6: Risk scoring
# ---------------------------
high_amount = 100000

def risk_score(row):
    if row['is_suspicious'] == 'Yes':
        return 'High'
    elif row['total_amount'] > high_amount:
        return 'Medium'
    else:
        return 'Low'

kyc_df['risk_level'] = kyc_df.apply(risk_score, axis=1)

# ---------------------------
# Step 7: Save Detailed Report & Summary
# ---------------------------
kyc_df.to_csv('kyc_aml_detailed_report.csv', index=False)
summary = kyc_df['risk_level'].value_counts().reset_index()
summary.columns = ['risk_level', 'num_customers']
summary.to_csv('kyc_aml_summary.csv', index=False)

print(" Detailed risk report generated successfully!")
print("Summary stats generated successfully!")

# ---------------------------
# Step 8: Prepare Dashboard
# ---------------------------
# Risk Level counts
risk_counts = kyc_df['risk_level'].value_counts().reindex(['High','Medium','Low']).fillna(0)

# Top 10 Customers
top10 = kyc_df.sort_values('total_amount', ascending=False).head(10)

# Suspicious counts
suspicious_counts = kyc_df['is_suspicious'].value_counts().reindex(['Yes','No']).fillna(0)

# ---------------------------
# Step 9: Create Dashboard
# ---------------------------
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=("Risk Level Distribution", "Top 10 Customers by Amount",
                    "Number of Transactions per Customer", "Suspicious vs Non-Suspicious"),
    specs=[[{"type":"bar"}, {"type":"bar"}],
           [{"type":"histogram"}, {"type":"pie"}]]
)

# Risk Level Bar
fig.add_trace(
    go.Bar(
        x=risk_counts.index,
        y=risk_counts.values,
        marker_color=['#E74C3C','#F39C12','#27AE60'],
        text=risk_counts.values,
        textposition='auto',
        name='Risk Level'
    ),
    row=1, col=1
)

# Top 10 Customers Bar with gradient and High Risk highlight
max_amt = top10['total_amount'].max()
min_amt = top10['total_amount'].min()
def blue_gradient(val):
    ratio = (val - min_amt)/(max_amt - min_amt + 1e-6)
    r,g,b = 100 + int(155*ratio), 181 + int(50*ratio), 246
    return f'rgb({r},{g},{b})'

top10_colors = [blue_gradient(v) for v in top10['total_amount']]
for i, risk in enumerate(top10['risk_level']):
    if risk == 'High':
        top10_colors[i] = '#E57373'  # soft red

fig.add_trace(
    go.Bar(
        x=top10['customerid'],
        y=top10['total_amount'],
        marker_color=top10_colors,
        text=top10['total_amount'],
        textposition='auto',
        name='Top Customers'
    ),
    row=1, col=2
)

# Number of Transactions Histogram
fig.add_trace(
    go.Histogram(
        x=kyc_df['num_transactions'],
        nbinsx=20,
        marker_color='#8E44AD',
        name='Transactions Count'
    ),
    row=2, col=1
)

# Suspicious Pie
fig.add_trace(
    go.Pie(
        labels=suspicious_counts.index,
        values=suspicious_counts.values,
        marker_colors=['#E74C3C','#2ECC71'],
        hole=0.3,
        name='Suspicious'
    ),
    row=2, col=2
)

# Layout
fig.update_layout(
    height=800, width=1000,
    title_text="KYC/AML Risk Dashboard",
    showlegend=True,
    template="plotly_white"
)

# Show & Save
fig.show()
fig.write_html("kyc_aml_dashboard.html")
