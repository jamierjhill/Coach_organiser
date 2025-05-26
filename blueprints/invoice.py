import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, flash, url_for, jsonify
from flask_login import login_required, current_user
from user_utils import load_json_feature, save_json_feature

invoice_bp = Blueprint("invoice", __name__)

INVOICES_DIR = "data/invoices"
TEMPLATES_DIR = "data/invoice_templates"

# Ensure directories exist
os.makedirs(INVOICES_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

def generate_invoice_number():
    """Generate a simple invoice number based on date and random digits."""
    date_part = datetime.now().strftime("%y%m%d")
    count = len(load_json_feature(INVOICES_DIR, current_user.username)) + 1
    return f"INV-{date_part}-{count:03d}"

def normalize_invoice_data(invoice):
    """Ensure invoice has consistent field names for templates."""
    if "total_amount" not in invoice and "amount" in invoice:
        invoice["total_amount"] = invoice["amount"]
    elif "amount" not in invoice and "total_amount" in invoice:
        invoice["amount"] = invoice["total_amount"]
    elif "total_amount" not in invoice and "amount" not in invoice:
        invoice["total_amount"] = invoice["amount"] = 0
    
    invoice.setdefault("status", "unpaid")
    invoice.setdefault("client_name", "Unknown Client")
    invoice.setdefault("description", "")
    invoice.setdefault("notes", "")
    invoice.setdefault("issue_date", datetime.now().strftime("%Y-%m-%d"))
    invoice.setdefault("due_date", datetime.now().strftime("%Y-%m-%d"))
    
    return invoice

# === TEMPLATE MANAGEMENT ===

@invoice_bp.route("/invoices/templates")
@login_required
def manage_templates():
    """Manage invoice templates."""
    try:
        templates = load_json_feature(TEMPLATES_DIR, current_user.username)
        return render_template("invoice_templates.html", templates=templates)
    except Exception as e:
        flash(f"❌ Error loading templates: {str(e)}", "danger")
        return render_template("invoice_templates.html", templates=[])

@invoice_bp.route("/invoices/templates/create", methods=["POST"])
@login_required
def create_template():
    """Create a new invoice template."""
    try:
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        amount = request.form.get("amount", "0").strip()
        notes = request.form.get("notes", "").strip()
        
        if not name or not description or not amount:
            flash("❌ Please fill in all required fields.", "danger")
            return redirect(url_for("invoice.manage_templates"))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash("❌ Amount must be greater than 0.", "danger")
                return redirect(url_for("invoice.manage_templates"))
        except ValueError:
            flash("❌ Amount must be a valid number.", "danger")
            return redirect(url_for("invoice.manage_templates"))
        
        # Create new template
        new_template = {
            "id": str(datetime.now().timestamp()).replace(".", ""),
            "name": name,
            "description": description,
            "amount": amount,
            "notes": notes,
            "created_at": datetime.now().isoformat()
        }
        
        templates = load_json_feature(TEMPLATES_DIR, current_user.username)
        templates.append(new_template)
        save_json_feature(TEMPLATES_DIR, current_user.username, templates)
        
        flash("✅ Template created successfully!", "success")
    except Exception as e:
        flash(f"❌ Error creating template: {str(e)}", "danger")
    
    return redirect(url_for("invoice.manage_templates"))

@invoice_bp.route("/invoices/templates/delete/<template_id>", methods=["POST"])
@login_required
def delete_template(template_id):
    """Delete an invoice template."""
    try:
        templates = load_json_feature(TEMPLATES_DIR, current_user.username)
        original_count = len(templates)
        templates = [t for t in templates if t.get("id") != template_id]
        
        if len(templates) == original_count:
            flash("❌ Template not found.", "danger")
        else:
            save_json_feature(TEMPLATES_DIR, current_user.username, templates)
            flash("✅ Template deleted successfully!", "success")
    except Exception as e:
        flash(f"❌ Error deleting template: {str(e)}", "danger")
    
    return redirect(url_for("invoice.manage_templates"))

@invoice_bp.route("/invoices/api/templates")
@login_required
def get_templates_api():
    """API endpoint to get templates for AJAX requests."""
    try:
        templates = load_json_feature(TEMPLATES_DIR, current_user.username)
        return jsonify({"success": True, "templates": templates})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# === EXISTING INVOICE ROUTES (Updated) ===

@invoice_bp.route("/invoices")
@login_required
def invoice_list():
    """Display the simplified invoice dashboard with clear paid/unpaid sections."""
    try:
        invoices = load_json_feature(INVOICES_DIR, current_user.username)
        invoices = [normalize_invoice_data(inv) for inv in invoices]
        invoices.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
        unpaid_invoices = [inv for inv in invoices if inv.get("status") in ["unpaid", "overdue"]]
        
        # Check for overdue invoices and update status
        today = datetime.now().date()
        updated = False
        for invoice in unpaid_invoices:
            try:
                due_date = datetime.strptime(invoice.get("due_date", ""), "%Y-%m-%d").date()
                if due_date < today and invoice.get("status") != "overdue":
                    invoice["status"] = "overdue"
                    updated = True
            except ValueError:
                continue
        
        if updated:
            save_json_feature(INVOICES_DIR, current_user.username, invoices)
        
        total_paid = sum(float(inv.get("total_amount", 0)) for inv in paid_invoices)
        total_unpaid = sum(float(inv.get("total_amount", 0)) for inv in unpaid_invoices)
        num_overdue = sum(1 for inv in unpaid_invoices if inv.get("status") == "overdue")
        
        return render_template(
            "invoice_list.html",
            paid_invoices=paid_invoices,
            unpaid_invoices=unpaid_invoices,
            total_paid=total_paid,
            total_unpaid=total_unpaid,
            num_overdue=num_overdue
        )
    except Exception as e:
        flash(f"❌ Error loading invoices: {str(e)}", "danger")
        return render_template(
            "invoice_list.html",
            paid_invoices=[],
            unpaid_invoices=[],
            total_paid=0,
            total_unpaid=0,
            num_overdue=0
        )

@invoice_bp.route("/invoices/create", methods=["GET", "POST"])
@login_required
def create_invoice():
    """Create a new invoice with template support."""
    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        description = request.form.get("description", "").strip()
        amount = request.form.get("amount", "0").strip()
        due_date = request.form.get("due_date", "")
        notes = request.form.get("notes", "").strip()
        
        if not client_name or not description or not amount:
            flash("❌ Please fill in all required fields.", "danger")
            return redirect(url_for("invoice.create_invoice"))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash("❌ Amount must be greater than 0.", "danger")
                return redirect(url_for("invoice.create_invoice"))
        except ValueError:
            flash("❌ Amount must be a valid number.", "danger")
            return redirect(url_for("invoice.create_invoice"))
        
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            flash("❌ Please provide a valid due date.", "danger")
            return redirect(url_for("invoice.create_invoice"))
        
        new_invoice = {
            "id": str(datetime.now().timestamp()).replace(".", ""),
            "invoice_number": generate_invoice_number(),
            "client_name": client_name,
            "description": description,
            "amount": amount,
            "total_amount": amount,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": due_date,
            "notes": notes,
            "status": "unpaid",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "coach_name": current_user.username
        }
        
        try:
            invoices = load_json_feature(INVOICES_DIR, current_user.username)
            invoices.append(new_invoice)
            save_json_feature(INVOICES_DIR, current_user.username, invoices)
            
            flash("✅ Invoice created successfully!", "success")
            return redirect(url_for("invoice.invoice_list"))
        except Exception as e:
            flash(f"❌ Error saving invoice: {str(e)}", "danger")
            return redirect(url_for("invoice.create_invoice"))
    
    # Handle duplicate functionality
    duplicate_from = None
    is_duplicate = False
    
    if request.args.get("duplicate"):
        try:
            invoices = load_json_feature(INVOICES_DIR, current_user.username)
            duplicate_from = next((inv for inv in invoices if inv.get("id") == request.args.get("duplicate")), None)
            is_duplicate = True
        except:
            duplicate_from = None
    
    # Load templates for quick selection
    templates = load_json_feature(TEMPLATES_DIR, current_user.username)
    
    default_due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    return render_template(
        "invoice_create.html", 
        due_date=default_due_date,
        duplicate_from=duplicate_from,
        is_duplicate=is_duplicate,
        templates=templates
    )

@invoice_bp.route("/invoices/view/<invoice_id>")
@login_required
def view_invoice(invoice_id):
    """View a specific invoice."""
    try:
        invoices = load_json_feature(INVOICES_DIR, current_user.username)
        invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
        
        if not invoice:
            flash("❌ Invoice not found.", "danger")
            return redirect(url_for("invoice.invoice_list"))
        
        invoice = normalize_invoice_data(invoice)
        return render_template("invoice_view.html", invoice=invoice)
    except Exception as e:
        flash(f"❌ Error loading invoice: {str(e)}", "danger")
        return redirect(url_for("invoice.invoice_list"))

@invoice_bp.route("/invoices/mark-paid/<invoice_id>", methods=["POST"])
@login_required
def mark_paid(invoice_id):
    """Simple one-click action to mark invoice as paid."""
    try:
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
    except Exception as e:
        flash(f"❌ Error updating invoice: {str(e)}", "danger")
    
    return redirect(url_for("invoice.invoice_list"))

@invoice_bp.route("/invoices/delete/<invoice_id>", methods=["POST"])
@login_required
def delete_invoice(invoice_id):
    """Delete an invoice."""
    try:
        invoices = load_json_feature(INVOICES_DIR, current_user.username)
        original_count = len(invoices)
        invoices = [inv for inv in invoices if inv.get("id") != invoice_id]
        
        if len(invoices) == original_count:
            flash("❌ Invoice not found.", "danger")
        else:
            save_json_feature(INVOICES_DIR, current_user.username, invoices)
            flash("✅ Invoice deleted successfully!", "success")
    except Exception as e:
        flash(f"❌ Error deleting invoice: {str(e)}", "danger")
    
    return redirect(url_for("invoice.invoice_list"))

@invoice_bp.route("/invoices/duplicate/<invoice_id>")
@login_required
def duplicate_invoice(invoice_id):
    """Create a new invoice based on an existing one."""
    try:
        invoices = load_json_feature(INVOICES_DIR, current_user.username)
        original_invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
        
        if not original_invoice:
            flash("❌ Original invoice not found.", "danger")
            return redirect(url_for("invoice.invoice_list"))
        
        templates = load_json_feature(TEMPLATES_DIR, current_user.username)
        default_due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        return render_template(
            "invoice_create.html", 
            due_date=default_due_date,
            duplicate_from=original_invoice,
            is_duplicate=True,
            templates=templates
        )
    except Exception as e:
        flash(f"❌ Error duplicating invoice: {str(e)}", "danger")
        return redirect(url_for("invoice.invoice_list"))