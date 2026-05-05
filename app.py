from flask import Flask, render_template, request

app = Flask(__name__)


def parse_float(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def calculate_mortgage(loan_amount: float, years: int, annual_rate: float) -> dict:
    months = years * 12
    monthly_rate = annual_rate / 100 / 12

    if months <= 0:
        raise ValueError("Срок кредита должен быть больше 0.")
    if loan_amount <= 0:
        raise ValueError("Сумма кредита должна быть больше 0.")
    if annual_rate < 0:
        raise ValueError("Процентная ставка не может быть отрицательной.")

    if monthly_rate == 0:
        base_monthly_payment = round(loan_amount / months, 2)
    else:
        raw_payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** months
        ) / ((1 + monthly_rate) ** months - 1)
        # Banks usually display payment rounded to kopeks.
        base_monthly_payment = round(raw_payment, 2)

    schedule = []
    balance = round(loan_amount, 2)
    total_interest = 0.0
    total_payment = 0.0

    for month in range(1, months + 1):
        interest_payment = round(balance * monthly_rate, 2)

        if month == months:
            principal_payment = balance
            payment = round(principal_payment + interest_payment, 2)
        else:
            payment = base_monthly_payment
            principal_payment = round(payment - interest_payment, 2)
            if principal_payment <= 0:
                raise ValueError(
                    "Слишком высокая ставка или слишком короткий срок: платеж не покрывает проценты."
                )
            if principal_payment > balance:
                principal_payment = balance
                payment = round(principal_payment + interest_payment, 2)

        balance = round(balance - principal_payment, 2)
        if balance < 0:
            balance = 0.0

        total_interest = round(total_interest + interest_payment, 2)
        total_payment = round(total_payment + payment, 2)

        schedule.append(
            {
                "month": month,
                "payment": payment,
                "interest": interest_payment,
                "principal": principal_payment,
                "balance": balance,
            }
        )

    overpayment = total_interest
    # Conservative guideline: mortgage payment should be <= 40% income.
    required_income = base_monthly_payment / 0.4
    return {
        "monthly_payment": base_monthly_payment,
        "total_payment": total_payment,
        "overpayment": overpayment,
        "required_income": required_income,
        "schedule": schedule,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    form_data = {
        "property_price": "",
        "down_payment": "",
        "years": "",
        "rate": "",
    }

    if request.method == "POST":
        form_data = {
            "property_price": request.form.get("property_price", "").strip(),
            "down_payment": request.form.get("down_payment", "").strip(),
            "years": request.form.get("years", "").strip(),
            "rate": request.form.get("rate", "").strip(),
        }
        try:
            property_price = parse_float(form_data["property_price"] or "0")
            down_payment = parse_float(form_data["down_payment"] or "0")
            years = int(form_data["years"])
            annual_rate = parse_float(form_data["rate"] or "0")
            loan_amount = property_price - down_payment

            if property_price <= 0:
                raise ValueError("Стоимость недвижимости должна быть больше 0.")
            if down_payment < 0:
                raise ValueError("Первоначальный взнос не может быть отрицательным.")
            if down_payment >= property_price:
                raise ValueError("Первоначальный взнос должен быть меньше стоимости недвижимости.")

            calc = calculate_mortgage(loan_amount, years, annual_rate)
            down_payment_percent = (down_payment / property_price) * 100
            result = {
                "property_price": property_price,
                "down_payment": down_payment,
                "down_payment_percent": round(down_payment_percent, 2),
                "loan_amount": loan_amount,
                "years": years,
                "rate": annual_rate,
                "monthly_payment": round(calc["monthly_payment"], 2),
                "total_payment": round(calc["total_payment"], 2),
                "overpayment": round(calc["overpayment"], 2),
                "required_income": round(calc["required_income"], 2),
                "schedule": calc["schedule"],
            }
        except ValueError as exc:
            error = str(exc)
        except Exception:
            error = "Проверьте корректность введенных данных."

    return render_template("index.html", result=result, error=error, form_data=form_data)


if __name__ == "__main__":
    app.run(debug=True)
