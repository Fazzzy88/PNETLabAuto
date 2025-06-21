import os
import subprocess

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LAB_DATA = os.path.join(BASE_DIR, "lab_data")
LAB_SCRIPTS = os.path.join(BASE_DIR, "lab_scripts")


def get_student_dirs(lab_name):
    lab_path = os.path.join(LAB_DATA, lab_name)
    return sorted([
        d for d in os.listdir(lab_path)
        if os.path.isdir(os.path.join(lab_path, d))
    ])


@app.route("/")
def index():
    labs = sorted(os.listdir(LAB_DATA))
    return render_template("index.html", labs=labs)


@app.route("/check/<lab_name>")
def view_lab(lab_name):
    students = get_student_dirs(lab_name)
    return render_template("check.html", lab=lab_name, students=students)


@app.route("/run_check", methods=["POST"])
def run_check():
    data = request.json
    lab_name = data.get("lab")
    selected_students = data.get("students", [])
    run_all = data.get("run_all", False)

    if run_all:
        selected_students = get_student_dirs(lab_name)

    results = {}

    for student in selected_students:
        script_path = os.path.join(LAB_SCRIPTS, f"{lab_name.lower()}_check.py")
        lab_path = os.path.join(LAB_DATA, lab_name, student)
        node_file = os.path.join(lab_path, "node_sessions.xls")
        result_file = os.path.join(lab_path, "result.txt")

        if not os.path.exists(script_path) or not os.path.exists(node_file):
            results[student] = "❌ Скрипт или node_sessions.xls не найдены"
            continue

        try:
            with open(result_file, "w") as f:
                proc = subprocess.Popen(
                    ["python3", script_path, node_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                output = ""
                for line in proc.stdout:
                    f.write(line)
                    output += line
                    # (можно сохранить логи в памяти, если хочешь real-time через WebSocket)
                proc.wait()
                results[student] = "✅ Готово"
        except Exception as e:
            results[student] = f"❌ Ошибка: {e}"

    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True)
