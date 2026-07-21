# Amazon Deals Telegram Bot

Automatically fetch the latest **Amazon India Deals**, retrieve product details using the **Amazon Product Advertising API (PA-API)**, and publish them to a **Telegram channel** with affiliate links.

## ✨ Features

* 🔍 Scrapes Amazon India Deals page for product ASINs
* 📦 Retrieves product details using Amazon PA-API
* 💰 Displays current price, MRP, and discount
* 🖼️ Sends product images to Telegram
* 🔗 Generates Amazon affiliate links
* 🤖 Automatic Telegram posting
* ⏱️ Hourly auto-refresh using Streamlit
* 🔄 Exponential backoff and retry mechanism for API rate limits

---

## 🛠️ Tech Stack

* Python 3.11
* Streamlit
* Amazon Product Advertising API (PA-API)
* Telegram Bot API
* BeautifulSoup4
* Requests

---

## 📂 Project Structure

```text
amazon-deals-telegram-bot/
│
├── app.py
├── requirements.txt
├── README.md
└── .devcontainer/
    └── devcontainer.json
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/amazon-deals-telegram-bot.git
cd amazon-deals-telegram-bot
```

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Configure Secrets

Create the following file:

```text
.streamlit/secrets.toml
```

Add your credentials:

```toml
AMAZON_ACCESS_KEY="YOUR_ACCESS_KEY"
AMAZON_SECRET_KEY="YOUR_SECRET_KEY"
AMAZON_ASSOC_TAG="YOUR_ASSOCIATE_TAG"

TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
TELEGRAM_CHANNEL_ID="YOUR_CHANNEL_ID"
```

> **Important:** Never commit `secrets.toml` to GitHub.

---

### 4. Run the application

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

---

## ⚙️ How It Works

```text
Amazon Deals Page
        │
        ▼
Extract Product ASINs
        │
        ▼
Amazon Product Advertising API
        │
        ▼
Retrieve Product Details
        │
        ▼
Generate Affiliate Link
        │
        ▼
Format Telegram Message
        │
        ▼
Send to Telegram Channel
```

---

## 📩 Telegram Message Example

```
🛒 Amazon Deal Alert!

📦 Logitech Wireless Mouse

💰 Price: ₹799
🏷️ MRP: ₹1,499
🎯 Discount: ₹700 (46.7% off)

🔗 https://amazon.in/dp/BXXXXXXXXX?tag=YOUR_ASSOCIATE_TAG
```

---

## 🔐 Environment Variables

| Variable            | Description                   |
| ------------------- | ----------------------------- |
| AMAZON_ACCESS_KEY   | Amazon PA-API Access Key      |
| AMAZON_SECRET_KEY   | Amazon PA-API Secret Key      |
| AMAZON_ASSOC_TAG    | Amazon Associates Tracking ID |
| TELEGRAM_BOT_TOKEN  | Telegram Bot Token            |
| TELEGRAM_CHANNEL_ID | Telegram Channel ID           |

---

## 📌 Requirements

* Python 3.11+
* Amazon Associates Account
* Amazon Product Advertising API Access
* Telegram Bot
* Telegram Channel with Bot as Admin

---

## 📋 TODO

* [ ] Async API requests
* [ ] Duplicate deal detection
* [ ] SQLite/PostgreSQL support
* [ ] Product category filtering
* [ ] Price history tracking
* [ ] Web dashboard
* [ ] Docker support
* [ ] Multi-channel Telegram support

---

## ⚠️ Disclaimer

This project is intended for educational and automation purposes.

Please ensure you comply with:

* Amazon Product Advertising API Terms of Service
* Amazon Associates Program Policies
* Telegram Bot API Terms

---

## 📄 License

This project is licensed under the MIT License.

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
