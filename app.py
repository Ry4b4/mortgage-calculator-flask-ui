from flask import Flask, render_template, request

app = Flask(__name__)


def parse_float(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def calculate_mortgage(principal: float, years: int, annual_rate: float) -> dict:
    """
    Calculate total overpayment for an annuity mortgage.
    overpayment = total paid - principal
    """
    months = years * 12
    monthly_rate = annual_rate / 100 / 12

    if months <= 0:
        raise ValueError("Срок кредита должен быть больше 0.")
    if principal <= 0:
        raise ValueError("Сумма кредита должна быть больше 0.")
    if annual_rate < 0:
        raise ValueError("Процентная ставка не может быть отрицательной.")

    if monthly_rate == 0:
        monthly_payment = principal / months
    else:
        monthly_payment = principal * (
            monthly_rate * (1 + monthly_rate) ** months
        ) / ((1 + monthly_rate) ** months - 1)
    total_payment = monthly_payment * months

    overpayment = total_payment - principal
    # Conservative guideline: mortgage payment should be <= 40% income.
    required_income = monthly_payment / 0.4
    return {
        "monthly_payment": monthly_payment,
        "total_payment": total_payment,
        "overpayment": overpayment,
        "required_income": required_income,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    form_data = {
        "principal": "",
        "years": "",
        "rate": "",
    }

    if request.method == "POST":
        form_data = {
            "principal": request.form.get("principal", "").strip(),
            "years": request.form.get("years", "").strip(),
            "rate": request.form.get("rate", "").strip(),
        }
        try:
            principal = parse_float(form_data["principal"] or "0")
            years = int(form_data["years"])
            annual_rate = parse_float(form_data["rate"] or "0")

            calc = calculate_mortgage(principal, years, annual_rate)
            result = {
                "principal": principal,
                "years": years,
                "rate": annual_rate,
                "monthly_payment": round(calc["monthly_payment"], 2),
                "total_payment": round(calc["total_payment"], 2),
                "overpayment": round(calc["overpayment"], 2),
                "required_income": round(calc["required_income"], 2),
            }
        except ValueError as exc:
            error = str(exc)
        except Exception:
            error = "Проверьте корректность введенных данных."

    return render_template("index.html", result=result, error=error, form_data=form_data)


if __name__ == "__main__":
    app.run(debug=True)
