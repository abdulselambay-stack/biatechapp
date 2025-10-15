# TechnoSender Modularization Guide

## ✅ Modularization Complete

The application has been successfully refactored from a single `app.py` (~2700 lines) into a modular blueprint-based architecture.

## 📁 New Structure

```
wpCloud/
├── app.py                  # Main Flask app (70 lines)
├── routes/                 # Blueprint modules
│   ├── __init__.py        # Blueprint registration
│   ├── auth.py            # Authentication & sessions
│   ├── webhook.py         # WhatsApp webhooks
│   ├── contacts.py        # Contact management
│   ├── chat.py            # Chat interface
│   ├── analytics.py       # Dashboard & analytics
│   ├── bulk_send.py       # Bulk messaging
│   ├── messages.py        # Direct messaging
│   ├── products.py        # Product management
│   ├── sales.py           # Sales tracking
│   ├── templates.py       # Template management
│   └── pages.py           # Misc pages (campaigns, settings)
├── utils.py               # WhatsApp API helpers
├── models.py              # Database models
└── database.py            # MongoDB connection

```

## 🔑 Environment Variables

Required variables in `.env`:

```bash
# WhatsApp Cloud API
WHATSAPP_ACCESS_TOKEN=your_access_token_here
PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_BUSINESS_ID=your_business_id_here

# Webhook
VERIFY_TOKEN=technoglobal123

# Database
MONGODB_URI=mongodb+srv://...

# Security
SECRET_KEY=your-secret-key
```

## 🚀 Running the Application

### Development
```bash
python3 app.py
```

### Production (with Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:5005 app:app
```

## 📋 All Routes (49 total)

### Authentication
- `GET/POST /login` - Login page & API
- `GET /logout` - Logout
- `POST /api/login` - AJAX login
- `POST /api/logout` - AJAX logout

### Webhooks
- `GET /health` - Health check
- `GET /webhook/test` - Webhook test
- `GET /webhook` - Webhook verification
- `POST /webhook` - Webhook receiver

### Contacts
- `GET /contacts` - Contacts page
- `GET /api/contacts-mongo` - List contacts
- `POST /api/contacts-mongo` - Create contact
- `GET /api/contacts-mongo/<phone>` - Get contact
- `PUT /api/contacts-mongo/<phone>` - Update contact
- `DELETE /api/contacts-mongo/<phone>` - Delete contact
- `GET /api/contacts/sent-templates/<phone>` - Sent templates

### Chat
- `GET /chat` - Chat page
- `GET /api/chats` - List chats
- `GET /api/chat/<phone>` - Chat history
- `POST /api/chat/<phone>/mark-read` - Mark as read
- `GET /api/chat/unread-count` - Unread count

### Analytics & Dashboard
- `GET /` - Main dashboard
- `GET /analytics` - Analytics page
- `GET /api/analytics/stats` - Statistics (with time range)

### Bulk Send
- `GET /bulk-send` - Bulk send page
- `GET /api/bulk-send/preview` - Preview recipients
- `POST /api/bulk-send` - Send bulk messages
- `GET /api/bulk-send/logs` - Send logs

### Messages
- `POST /api/send-message` - Send text message
- `POST /api/send-image` - Send image message

### Products
- `GET /products` - Products page
- `GET /api/products` - List products
- `POST /api/products` - Create product
- `GET /api/products/<id>` - Get product
- `PUT /api/products/<id>` - Update product
- `DELETE /api/products/<id>` - Delete product

### Sales
- `GET /sales` - Sales page
- `GET /api/sales` - List sales
- `POST /api/sales` - Create sale
- `GET /api/sales/<id>` - Get sale
- `PUT /api/sales/<id>` - Update sale
- `DELETE /api/sales/<id>` - Delete sale

### Templates
- `GET /api/templates` - List templates from Meta
- `GET /api/templates/<name>/image-id` - Get template image ID
- `POST /api/templates/<name>/image-id` - Save template image ID

### Pages
- `GET /campaigns` - Campaigns page
- `GET /settings` - Settings page
- `GET /template-management` - Template management page

### Utility
- `GET /uploads/<filename>` - Serve uploaded files

## 🔧 Key Improvements

1. **Modular Architecture**: Each feature has its own blueprint
2. **Single Source of Truth**: `login_required` decorator in `auth.py`
3. **Consistent Session Management**: All routes use `logged_in` session key
4. **Environment Variable Compatibility**: Supports both `WHATSAPP_ACCESS_TOKEN` and `ACCESS_TOKEN`
5. **Centralized Utilities**: WhatsApp API calls in `utils.py`
6. **Clean Main App**: Only 70 lines in `app.py`

## 🐛 Fixed Issues

1. ✅ Session key mismatch (`user_id` vs `logged_in`)
2. ✅ Environment variable inconsistency (`ACCESS_TOKEN` vs `WHATSAPP_ACCESS_TOKEN`)
3. ✅ VERIFY_TOKEN default value alignment
4. ✅ Duplicate route definitions
5. ✅ Missing API endpoints (`/api/login`, `/api/logout`)

## 📝 Notes

- Old app.py backed up as `app_old.py`
- All existing functionality preserved
- Database models unchanged
- Frontend templates compatible with new routes
- All 11 blueprints loaded successfully

## 🧪 Testing

Run the test script to verify all routes:
```bash
python3 test_routes.py
```

Expected output: ✅ 49 routes registered successfully
