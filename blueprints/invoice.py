import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user
from user_utils import load_json_feature, save_json_feature

invoice_bp = Blueprint("invoice", __name__)

INVOICES_DIR = "data/invoices"

# Ensure invoices directory exists
os.makedirs(INVOICES_DIR, exist_ok=True)

def generate_invoice_number():
    """Generate a simple invoice number based on date and random digits."""
    date_part = datetime.now().strftime("%y%m%d")
    count = len(load_json_feature(INVOICES_DIR, current_user.username)) + 1
    return f"INV-{date_part}-{count:03d}"

@invoice_bp.route("/invoices")
@login_required
def invoice_list():
    """Display the simplified invoice dashboard with clear paid/unpaid sections."""
    invoices = load_json_feature(INVOICES_DIR, current_user.username)
    
    # Sort invoices by date (newest first)
    invoices.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Separate into paid and unpaid
    paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
    unpaid_invoices = [inv for inv in invoices if inv.get("status") in ["unpaid", "overdue"]]
    
    # Check for overdue invoices and update status
    today = datetime.now().date()
    for invoice in unpaid_invoices:
        due_date = datetime.strptime(invoice.get("due_date", ""), "%Y-%m-%d").date()
        if due_date < today and invoice.get("status") != "overdue":
            invoice["status"] = "overdue"
            # We'll need to save the updated statuses
            save_json_feature(INVOICES_DIR, current_user.username, invoices)
    
    # Calculate totals
    total_paid = sum(float(inv.get("amount", 0)) for inv in paid_invoices)
    total_unpaid = sum(float(inv.get("amount", 0)) for inv in unpaid_invoices)
    num_overdue = sum(1 for inv in unpaid_invoices if inv.get("status") == "overdue")
    
    return render_template(
        "invoice_list.html",
        paid_invoices=paid_invoices,
        unpaid_invoices=unpaid_invoices,
        total_paid=total_paid,
        total_unpaid=total_unpaid,
        num_overdue=num_overdue
    )

@invoice_bp.route("/invoices/create", methods=["GET", "POST"])
@login_required
def create_invoice():
    """Create a new invoice with a simplified form."""
    if request.method == "POST":
        # Extract form data
        client_name = request.form.get("client_name", "").strip()
        description = request.form.get("description", "").strip()
        amount = request.form.get("amount", "0").strip()
        due_date = request.form.get("due_date", "")
        notes = request.form.get("notes", "").strip()
        
        # Basic validation
        if not client_name or not description or not amount:
            flash("❌ Please fill in all required fields.", "danger")
            return redirect(url_for("invoice.create_invoice"))
        
        try:
            amount = float(amount)
        except ValueError:
            flash("❌ Amount must be a valid number.", "danger")
            return redirect(url_for("invoice.create_invoice"))
        
        # Create new simplified invoice
        new_invoice = {
            "id": str(datetime.now().timestamp()),
            "invoice_number": generate_invoice_number(),
            "client_name": client_name,
            "description": description,
            "amount": amount,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": due_date,
            "notes": notes,
            "status": "unpaid",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Save invoice
        invoices = load_json_feature(INVOICES_DIR, current_user.username)
        invoices.append(new_invoice)
        save_json_feature(INVOICES_DIR, current_user.username, invoices)
        
        flash("✅ Invoice created successfully!", "success")
        return redirect(url_for("invoice.invoice_list"))
    
    # Default due date (7 days from now)
    default_due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    return render_template(
        "invoice_create.html", 
        due_date=default_due_date
    )

@invoice_bp.route("/invoices/view/<invoice_id>")
@login_required
def view_invoice(invoice_id):
    """View a specific invoice."""
    invoices = load_json_feature(INVOICES_DIR, current_user.username)
    invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
    
    if not invoice:
        flash("❌ Invoice not found.", "danger")
        return redirect(url_for("invoice.invoice_list"))
    
    return render_template("invoice_view.html", invoice=invoice)

@invoice_bp.route("/invoices/mark-paid/<invoice_id>", methods=["POST"])
@login_required
def mark_paid(invoice_id):
    """Simple one-click action to mark invoice as paid."""
    invoices = load_json_feature(INVOICES_DIR, current_user.username)
    invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
    
    if not invoice:
        flash("❌ Invoice not found.", "danger")
    else:
        invoice["status"] = "paid"
        invoice["updated_at"] = datetime.now().isoformat()
        invoice["paid_date"] = datetime.now().strftime("%Y-%m-%d")
        save_json_feature(INVOICES_DIR, current_user.username, invoices)
        flash("✅ Invoice marked as paid!", "success")
    
    return redirect(url_for("invoice.invoice_list"))

@invoice_bp.route("/invoices/delete/<invoice_id>", methods=["POST"])
@login_required
def delete_invoice(invoice_id):
    """Delete an invoice."""
    invoices = load_json_feature(INVOICES_DIR, current_user.username)
    invoices = [inv for inv in invoices if inv.get("id") != invoice_id]
    
    save_json_feature(INVOICES_DIR, current_user.username, invoices)
    
    flash("✅ Invoice deleted successfully!", "success")
    return redirect(url_for("invoice.invoice_list"))