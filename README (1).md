# Course Feedback System

This repository contains the **Course Feedback System** with both frontend and backend.  
The project allows students to submit course feedback and provides an admin dashboard for managing and analyzing responses.  

---

## 🚀 Deployment Links
- **Assignment Deployment:** [Lovable Hosted App](https://course-feedback-dash.lovable.app)  
- **Hugging Face Space (Frontend):** [HuggingFace Hosting](https://huggingface.co/spaces/roshcheeku/course-feedback/tree/main)  
- **Backend Source Code:** [GitHub Backend](https://github.com/roshcheeku/course-feedback)  

---

## 🖥️ Running the Project Locally

### 1. Clone the Repository
```bash
git clone https://github.com/roshcheeku/course-feedback.git
cd course-feedback
```

---

### 2. Backend Setup
The backend is built with **Node.js + Express** and connects to **MongoDB**.

#### Install dependencies
```bash
cd backend
npm install
```

#### Start backend server
```bash
npm run dev
```
The backend will start on [http://localhost:5000](http://localhost:5000) (or the port defined in your `.env`).

---

### 3. Frontend Setup
The frontend is built with **React / Vite** (adjust if you used something else).

#### Install dependencies
```bash
cd frontend
npm install
```

#### Start frontend server
```bash
npm run dev
```
Frontend will run on [http://localhost:3000](http://localhost:3000).

---

## 📦 MongoDB Setup

1. Install [MongoDB Community Edition](https://www.mongodb.com/try/download/community) or use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a new database (e.g., `course_feedback`).
3. Add collections for users and feedback.
4. Configure the connection string in your `.env` file (see below).  

⚠️ **Note:** Since the MongoDB instance used in deployment is secured, credentials are **not shared here**. A screenshot has been attached in the repo/docs for verification.  

---

## ⚙️ Example `.env` File
Create a `.env` file inside the **backend** directory with the following values:

```env
PORT=5000
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/course_feedback
JWT_SECRET=your_secret_key
```

---

## 🔑 Test Logins

### Admin Account
- **Email:** `admin123@example.com`  
- **Password:** `Admin@1234`  

### Student Account
- **Email:** `student@example.com`  
- **Password:** `Student@1234`  

---

## ✅ Features
- Student feedback submission
- Admin dashboard with analytics
- Secure authentication (JWT)
- MongoDB integration

---

## 📸 Screenshots
(Screenshots of secured MongoDB setup and UI should be attached here.)

---

## 🛠️ Tech Stack
- **Frontend:** React / Vite
- **Backend:** Node.js, Express
- **Database:** MongoDB (Atlas / Local)
- **Deployment:** Hugging Face Spaces + Lovable App
