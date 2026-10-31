import os
import time
import json
import csv
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

# 1. Конфигурация провайдеров
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": "openai/gpt-oss-120b",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "model": "gemini-3.8-flash",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": "openrouter/free",
    },
    "nvidea": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": "openrouter/free",
    },
    # "thinkingmachines": {
    #     "base_url": "https://openrouter.ai/api/v1",
    #     "api_key": os.getenv("OPENROUTER_API_KEY"),
    #     "model": "thinkingmachines/inkling:free",
    # }
}

# 2. Функция запроса с замером времени
def ask(provider_name: str, prompt: str) -> dict:
    cfg = PROVIDERS[provider_name]
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])

    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = time.perf_counter() - start
        text = response.choices[0].message.content
        usage = response.usage
        return {
            "provider": provider_name,
            "model": cfg["model"],
            "status": "ok",
            "elapsed_sec": round(elapsed, 3),
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "completion_tokens": usage.completion_tokens if usage else None,
            "total_tokens": usage.total_tokens if usage else None,
            "answer": text,
            "error": None,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "provider": provider_name,
            "model": cfg["model"],
            "status": "error",
            "elapsed_sec": round(elapsed, 3),
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "answer": None,
            "error": str(e),
        }

# 3. Сохранение результатов
def save_results(results: list, prompt: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("results", exist_ok=True)

    # JSON — полные данные
    json_path = f"results/comparison_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt, "timestamp": timestamp, "results": results},
                  f, ensure_ascii=False, indent=2)

    # CSV — таблица для Excel
    csv_path = f"results/comparison_{timestamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "provider", "model", "status", "elapsed_sec",
            "prompt_tokens", "completion_tokens", "total_tokens", "error"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in writer.fieldnames})

    # Отдельный файл с текстами ответов
    answers_path = f"results/answers_{timestamp}.md"
    with open(answers_path, "w", encoding="utf-8") as f:
        f.write(f"# Prompt\n\n{prompt}\n\n")
        for r in results:
            f.write(f"## {r['provider']} ({r['model']})\n\n")
            f.write(f"- Время: {r['elapsed_sec']} с\n")
            f.write(f"- Статус: {r['status']}\n\n")
            f.write(f"{r['answer'] or r['error']}\n\n---\n\n")

    return json_path, csv_path, answers_path

# 4. Вывод таблицы в консоль
def print_table(results: list):
    headers = ["Провайдер", "Модель", "Статус", "Время, с", "Токены", "Ошибка"]
    rows = []
    for r in results:
        rows.append([
            r["provider"],
            r["model"],
            r["status"],
            f"{r['elapsed_sec']:.3f}",
            str(r["total_tokens"] or "-"),
            (r["error"] or "")[:40],
        ])

    # Вычисляем ширину колонок
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    sep = "-+-".join("-" * w for w in widths)
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print(sep)
    for row in rows:
        print(" | ".join(str(c).ljust(w) for c, w in zip(row, widths)))

# 5. Основной сценарий
if __name__ == "__main__":
    prompt = "Объясни в одном предложении, что такое четырехугольник"

    results = []
    for name in PROVIDERS:
        print(f"Запрос к {name}...")
        results.append(ask(name, prompt))

    print("\n=== Результаты ===\n")
    print_table(results)

    json_path, csv_path, answers_path = save_results(results, prompt)
    print(f"\nСохранено:")
    print(f"  JSON:    {json_path}")
    print(f"  CSV:     {csv_path}")
    print(f"  Ответы:  {answers_path}")