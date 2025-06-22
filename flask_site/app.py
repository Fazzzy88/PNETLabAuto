import os
import sys
import time
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from pathlib import Path
import subprocess

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
LAB_DATA_DIR = BASE_DIR / "lab_data"
LAB_SCRIPTS_DIR = BASE_DIR / "lab_scripts"


@app.route("/")
def index():
    labs = sorted([d.name for d in LAB_DATA_DIR.iterdir() if d.is_dir()])
    return render_template("index.html", labs=labs)


@app.route("/lab/<lab_name>")
def view_lab(lab_name):
    lab_path = LAB_DATA_DIR / lab_name
    if not lab_path.exists():
        return "Лабораторная не найдена", 404

    students = sorted([d.name for d in lab_path.iterdir() if d.is_dir()])
    return render_template("check.html", lab=lab_name, students=students)


@app.route("/run_check/<lab_name>", methods=["POST"])
def run_check(lab_name):
    data = request.get_json()
    selected_students = data.get("students")

    lab_script = LAB_SCRIPTS_DIR / f"{lab_name.lower()}_check.py"
    print(f"🛠 Попытка запустить: {lab_script}")

    if not lab_script.exists():
        return jsonify({"error": f"Скрипт {lab_script.name} не найден"}), 400

    @stream_with_context
    def generate():
        yield f"📁 Проверка лабораторной: {lab_name}\n\n"

        lab_path = LAB_DATA_DIR / lab_name
        student_dirs = sorted([d for d in lab_path.iterdir() if d.is_dir()])
        to_check = student_dirs if not selected_students else [
            lab_path / s for s in selected_students if (lab_path / s).exists()
        ]

        for student_dir in to_check:
            student_name = student_dir.name
            yield f"\n👨‍🎓 Проверка: {student_name}\n"

            command = [sys.executable, str(lab_script), str(student_dir)]

            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                result_lines = []

                for line in iter(process.stdout.readline, ''):
                    result_lines.append(line)
                    yield line

                process.stdout.close()
                process.wait()

                # Сохраняем вывод в result.txt
                result_path = student_dir / "result.txt"
                with open(result_path, "w", encoding="utf-8") as f:
                    f.writelines(result_lines)

                yield f"📄 Результат сохранён в {result_path.relative_to(BASE_DIR)}\n"

            except Exception as e:
                yield f"❌ Ошибка при запуске для {student_name}: {e}\n"

        yield "\n✅ Проверка завершена.\n"

    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)
