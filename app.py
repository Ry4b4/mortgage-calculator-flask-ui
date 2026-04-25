from flask import Flask, render_template, request

app = Flask(__name__)


def calculate_overpayment(principal: float, years: int, annual_rate: float) -> float:
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
        total_payment = principal
    else:
        monthly_payment = principal * (
            monthly_rate * (1 + monthly_rate) ** months
        ) / ((1 + monthly_rate) ** months - 1)
        total_payment = monthly_payment * months

    return total_payment - principal


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        try:
            principal = float(request.form.get("principal", "0").replace(",", "."))
            years = int(request.form.get("years", "0"))
            annual_rate = float(request.form.get("rate", "0").replace(",", "."))

            overpayment = calculate_overpayment(principal, years, annual_rate)
            result = {
                "overpayment": round(overpayment, 2),
                "principal": principal,
                "years": years,
                "rate": annual_rate,
            }
        except ValueError as exc:
            error = str(exc)
        except Exception:
            error = "Проверьте корректность введенных данных."

    return render_template("index.html", result=result, error=error)


if __name__ == "__main__":
    app.run(debug=True)
