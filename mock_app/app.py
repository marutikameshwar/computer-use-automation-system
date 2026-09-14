from flask import Flask, render_template, request, redirect, url_for, flash
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key' # Required for flash messages

# Mock Database
MEMBERS = {
    "12345": {"name": "Alice Smith", "savings": "$12,450.00", "checking": "$1,200.50"},
    "54321": {"name": "Bob Jones", "savings": "$5,000.00", "checking": "$450.25"},
    "777": {"name": "Charlie Handoff", "savings": "$1,000.00", "checking": "$10.00"},
    "500": {"name": "System Crash Tester", "savings": "$0.00", "checking": "$0.00"},
    "888": {"name": "Popup Tester", "savings": "$888.00", "checking": "$88.00"}
}

@app.route('/')
def search():
    return render_template('search.html')

@app.route('/search_action', methods=['POST'])
def search_action():
    member_id = request.form.get('member_id')
    
    # Hard Stop Simulation: 500 crashes the legacy system completely
    if member_id == "500":
        error_html = """
        <h1>500 Internal Server Error</h1>
        <p>FATAL EXCEPTION: The legacy mainframe crashed.</p>
        <hr>
        <p style='color: green;'><i>Admin Tools:</i></p>
        <a href='/dashboard/500'><button>Resolve System Error (Admin Bypass)</button></a>
        """
        return error_html, 500
        
    # Deterministic Business Error: 999 always fails (graceful)
    if member_id == "999" or member_id not in MEMBERS:
        flash("Record not found", "error")
        return render_template('search.html')
    
    return redirect(url_for('dashboard', member_id=member_id))

@app.route('/dashboard/<member_id>')
def dashboard(member_id):
    if member_id not in MEMBERS:
        return redirect(url_for('search'))
    
    member = MEMBERS[member_id]
    return render_template('dashboard.html', member_id=member_id, member=member)

@app.route('/transaction/<member_id>', methods=['GET', 'POST'])
def transaction(member_id):
    if request.method == 'POST':
        # Simulate a transaction being processed
        amount = request.form.get('amount')
        account_type = request.form.get('account_type')
        return render_template('confirmation.html', member_id=member_id, amount=amount, account_type=account_type)
    
    return render_template('transaction.html', member_id=member_id)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
