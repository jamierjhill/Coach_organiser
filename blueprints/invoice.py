import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, flash, url_for, jsonify, current_app
from flask_login import login_required, current_user
from user_utils import load_json_feature, save_json_feature

# Skip WeasyPrint import entirely to avoid dependency issues
WEASYPRINT_AVAILABLE = False

invoice_bp = Blueprint("invoice", __name__)

INVOICES_DIR = "data/invoices"

# Ensure invoices directory exists
os.makedirs(INVOICES_DIR, exist_ok=True)

def generate_invoice_number():
    """Generate a unique invoice number based on date and random digits."""
    date_part = datetime.now().strftime("%y%m%d")
    random_part = str(uuid.uuid4().int)[:4]
    return f"INV-{date_part}-{random_part}"

@invoice_bp.route("/invoices")
@login_required
def invoice_list():
    """Display the invoice dashboard with clear paid/unpaid sections."""
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
    total_paid = sum(float(invoice.get("total_amount", 0)) for invoice in paid_invoices)
    total_unpaid = sum(float(invoice.get("total_amount", 0)) for invoice in unpaid_invoices)
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
    """Create a new invoice with line items."""
    if request.method == "POST":
        # Extract form data
        client_name = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        due_date = request.form.get("due_date", "")
        notes = request.form.get("notes", "").strip()
        
        # Get line items from form
        items = []
        item_descriptions = request.form.getlist("item_description[]")
        item_quantities = request.form.getlist("item_quantity[]")
        item_rates = request.form.getlist("item_rate[]")
        
        # Calculate total amount
        total_amount = 0
        
        for i in range(len(item_descriptions)):
            if i < len(item_quantities) and i < len(item_rates):
                description = item_descriptions[i].strip()
                try:
                    quantity = float(item_quantities[i])
                    rate = float(item_rates[i])
                    amount = quantity * rate
                    
                    if description and quantity > 0 and rate > 0:
                        items.append({
                            "description": description,
                            "quantity": quantity,
                            "rate": rate,
                            "amount": amount
                        })
                        total_amount += amount
                except ValueError:
                    pass
        
        # Basic validation
        if not client_name or not items:
            flash("❌ Please fill in client name and at least one line item.", "danger")
            return redirect(url_for("invoice.create_invoice"))
        
        # Create new invoice with line items
        new_invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": generate_invoice_number(),
            "client_name": client_name,
            "client_email": client_email,
            "items": items,
            "total_amount": total_amount,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": due_date,
            "notes": notes,
            "status": "unpaid",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "coach_name": current_user.username
        }
        
        # Save invoice
        invoices = load_json_feature(INVOICES_DIR, current_user.username)
        invoices.append(new_invoice)
        save_json_feature(INVOICES_DIR, current_user.username, invoices)
        
        flash("✅ Invoice created successfully!", "success")
        
        # Check if user wants to send via email
        if "send_email" in request.form and client_email:
            success = send_invoice_email(new_invoice)
            if success:
                flash("✅ Invoice sent via email!", "success")
            else:
                flash("⚠️ Email could not be sent. Check email configuration.", "warning")
        
        return redirect(url_for("invoice.invoice_list"))
    
    # Default due date (14 days from now)
    default_due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    
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
    
    # Calculate total amount (for safety)
    total = sum(item.get("amount", 0) for item in invoice.get("items", []))
    invoice["total_amount"] = total
    
    return render_template("invoice_view.html", invoice=invoice, pdf_available=WEASYPRINT_AVAILABLE)

@invoice_bp.route("/invoices/mark-paid/<invoice_id>", methods=["POST"])
@login_required
def mark_paid(invoice_id):
    """Mark invoice as paid."""
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

@invoice_bp.route("/invoices/export-pdf/<invoice_id>")
@login_required
def export_pdf(invoice_id):
    """Export invoice as PDF."""
    # Since WeasyPrint is not available, just inform the user
    flash("⚠️ PDF generation is not available on this system. Please use the print function instead.", "warning")
    return redirect(url_for("invoice.view_invoice", invoice_id=invoice_id))

@invoice_bp.route("/invoices/send-email/<invoice_id>", methods=["POST"])
@login_required
def send_email(invoice_id):
    """Send invoice via email."""
    invoices = load_json_feature(INVOICES_DIR, current_user.username)
    invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
    
    if not invoice:
        flash("❌ Invoice not found.", "danger")
        return redirect(url_for("invoice.invoice_list"))
    
    # Get email from form or use stored email
    client_email = request.form.get("client_email", invoice.get("client_email", "")).strip()
    
    if not client_email:
        flash("❌ Client email is required to send invoice.", "danger")
        return redirect(url_for("invoice.view_invoice", invoice_id=invoice_id))
    
    # Update invoice with email if not already stored
    if not invoice.get("client_email"):
        invoice["client_email"] = client_email
        save_json_feature(INVOICES_DIR, current_user.username, invoices)
    
    success = send_invoice_email(invoice)
    
    if success:
        flash("✅ Invoice sent via email!", "success")
    else:
        flash("⚠️ Email could not be sent. Check email configuration.", "warning")
    
    return redirect(url_for("invoice.view_invoice", invoice_id=invoice_id))

def send_invoice_email(invoice):
    """Helper function to send invoice via email."""
    try:
        # Get the mail extension from the current app
        mail = current_app.extensions.get("mail")
        if not mail:
            print("Mail extension not found in the current app")
            return False
            
        client_email = invoice.get("client_email")
        if not client_email:
            return False
        
        # Import Message class inside the function to avoid circular import
        from flask_mail import Message
        
        coach_name = current_user.username.capitalize()
        invoice_number = invoice.get("invoice_number")
        total_amount = invoice.get("total_amount", 0)
        
        subject = f"Invoice #{invoice_number} from {coach_name}"
        
        # Generate HTML for the invoice
        html_content = render_template("invoice_email.html", invoice=invoice)
        
        msg = Message(
            subject=subject,
            recipients=[client_email],
            html=html_content,
            sender=("Coaches Hub", current_user.username)
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

@invoice_bp.route("/api/invoice-template")
@login_required
def invoice_template():
    """Return a template for a new line item."""
    return jsonify({
        "html": render_template("partials/invoice_line_item.html", item_index=request.args.get("index", 0))
    })