import io
import json
from typing import Dict, List

from flask import Flask, Response, render_template, request
from openpyxl import Workbook

app = Flask(__name__)


def parse_float(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def calculate_annuity_payment(balance: float, monthly_rate: float, months_left: int) -> float:
    if months_left <= 0:
        return 0.0
    if monthly_rate == 0:
        return round(balance / months_left, 2)
    payment = balance * (monthly_rate * (1 + monthly_rate) ** months_left) / (
        (1 + monthly_rate) ** months_left - 1
    )
    return round(payment, 2)


def parse_early_payments(raw_payload: str) -> Dict[int, float]:
    if not raw_payload.strip():
        return {}
    items = json.loads(raw_payload)
    result: Dict[int, float] = {}
    for item in items:
        month = int(item.get("month", 0))
        amount_raw = str(item.get("amount", "0"))
        amount = parse_float(amount_raw)
        if month > 0 and amount > 0:
            result[month] = result.get(month, 0.0) + amount
    return result


def calculate_mortgage(
    loan_amount: float,
    years: int,
    annual_rate: float,
    early_payments: Dict[int, float],
    early_strategy: str,
) -> Dict:
    months = years * 12
    monthly_rate = annual_rate / 100 / 12

    if months <= 0:
        raise ValueError("Срок кредита должен быть больше 0.")
    if loan_amount <= 0:
        raise ValueError("Сумма кредита должна быть больше 0.")
    if annual_rate < 0:
        raise ValueError("Процентная ставка не может быть отрицательной.")
    if early_strategy not in ("reduce_payment", "reduce_term"):
        raise ValueError("Некорректная стратегия досрочного погашения.")

    monthly_payment = calculate_annuity_payment(loan_amount, monthly_rate, months)
    initial_monthly_payment = monthly_payment

    schedule: List[Dict] = []
    balance = round(loan_amount, 2)
    total_interest = 0.0
    total_paid = 0.0
    month = 0

    while balance > 0.0 and month < 1200:
        month += 1
        interest_payment = round(balance * monthly_rate, 2)
        regular_payment = monthly_payment
        principal_payment = round(regular_payment - interest_payment, 2)

        if principal_payment <= 0 and monthly_rate > 0:
            raise ValueError(
                "Платеж не покрывает проценты. Увеличьте срок или измените условия."
            )

        if principal_payment > balance:
            principal_payment = balance
            regular_payment = round(principal_payment + interest_payment, 2)

        balance = round(balance - principal_payment, 2)
        early_payment = round(min(early_payments.get(month, 0.0), balance), 2)
        balance = round(balance - early_payment, 2)
        if balance < 0:
            balance = 0.0

        month_total = round(regular_payment + early_payment, 2)
        total_interest = round(total_interest + interest_payment, 2)
        total_paid = round(total_paid + month_total, 2)

        schedule.append(
            {
                "month": month,
                "payment": month_total,
                "regular_payment": regular_payment,
                "interest": interest_payment,
                "principal": principal_payment + early_payment,
                "early_payment": early_payment,
                "balance": balance,
            }
        )

        if balance <= 0:
            break

        if early_strategy == "reduce_payment":
            months_left = max(months - month, 1)
            monthly_payment = calculate_annuity_payment(balance, monthly_rate, months_left)
        else:
            monthly_payment = initial_monthly_payment

    required_income = round(initial_monthly_payment / 0.4, 2)
    return {
        "monthly_payment": round(initial_monthly_payment, 2),
        "total_payment": total_paid,
        "overpayment": total_interest,
        "required_income": required_income,
        "schedule": schedule,
        "actual_months": len(schedule),
    }


def build_result(form_data: Dict[str, str]) -> Dict:
    property_price = parse_float(form_data["property_price"] or "0")
    down_payment = parse_float(form_data["down_payment"] or "0")
    years = int(form_data["years"])
    annual_rate = parse_float(form_data["rate"] or "0")
    early_strategy = form_data["early_strategy"]
    early_payments = parse_early_payments(form_data.get("early_payments", "[]"))
    loan_amount = property_price - down_payment

    if property_price <= 0:
        raise ValueError("Стоимость недвижимости должна быть больше 0.")
    if down_payment < 0:
        raise ValueError("Первоначальный взнос не может быть отрицательным.")
    if down_payment >= property_price:
        raise ValueError("Первоначальный взнос должен быть меньше стоимости недвижимости.")

    calc = calculate_mortgage(loan_amount, years, annual_rate, early_payments, early_strategy)
    down_payment_percent = round((down_payment / property_price) * 100, 2)

    return {
        "property_price": property_price,
        "down_payment": down_payment,
        "down_payment_percent": down_payment_percent,
        "loan_amount": loan_amount,
        "years": years,
        "rate": annual_rate,
        "monthly_payment": calc["monthly_payment"],
        "total_payment": calc["total_payment"],
        "overpayment": calc["overpayment"],
        "required_income": calc["required_income"],
        "schedule": calc["schedule"],
        "actual_months": calc["actual_months"],
    }


def form_defaults() -> Dict[str, str]:
    return {
        "property_price": "",
        "down_payment": "",
        "years": "",
        "rate": "",
        "mode": "mortgage",
        "early_strategy": "reduce_payment",
        "early_payments": "[]",
    }


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    form_data = form_defaults()

    if request.method == "POST":
        form_data = {
            "property_price": request.form.get("property_price", "").strip(),
            "down_payment": request.form.get("down_payment", "").strip(),
            "years": request.form.get("years", "").strip(),
            "rate": request.form.get("rate", "").strip(),
            "mode": request.form.get("mode", "mortgage").strip(),
            "early_strategy": request.form.get("early_strategy", "reduce_payment").strip(),
            "early_payments": request.form.get("early_payments", "[]").strip(),
        }
        if form_data["mode"] == "installment":
            form_data["rate"] = "0"

        try:
            result = build_result(form_data)
        except ValueError as exc:
            error = str(exc)
        except Exception:
            error = "Проверьте корректность введенных данных."

    return render_template("index.html", result=result, error=error, form_data=form_data)


@app.route("/export", methods=["POST"])
def export_schedule():
    form_data = {
        "property_price": request.form.get("property_price", "").strip(),
        "down_payment": request.form.get("down_payment", "").strip(),
        "years": request.form.get("years", "").strip(),
        "rate": request.form.get("rate", "").strip(),
        "mode": request.form.get("mode", "mortgage").strip(),
        "early_strategy": request.form.get("early_strategy", "reduce_payment").strip(),
        "early_payments": request.form.get("early_payments", "[]").strip(),
    }
    if form_data["mode"] == "installment":
        form_data["rate"] = "0"

    result = build_result(form_data)
    wb = Workbook()
    ws = wb.active
    ws.title = "График платежей"
    ws.append(["Месяц", "Платеж", "Регулярный платеж", "Проценты", "Тело кредита", "Досрочно", "Остаток"])
    for row in result["schedule"]:
        ws.append(
            [
                row["month"],
                row["payment"],
                row["regular_payment"],
                row["interest"],
                row["principal"],
                row["early_payment"],
                row["balance"],
            ]
        )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=mortgage_schedule.xlsx"},
    )


if __name__ == "__main__":
    app.run(debug=True)
