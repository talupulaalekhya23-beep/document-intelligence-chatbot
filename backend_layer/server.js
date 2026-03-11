import express from "express";
import fetch from "node-fetch";
import cors from "cors";
import dotenv from "dotenv";
import swaggerUi from "swagger-ui-express";
import swaggerJSDoc from "swagger-jsdoc";
import multer from "multer";
import fs from "fs";
import FormData from "form-data";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json({ limit: "1mb" }));

const NODE_PORT = Number(process.env.NODE_PORT || 3000);
const AI_BASE_URL = process.env.AI_BASE_URL || "http://localhost:8000";

/* ---------------- File Upload Config ---------------- */

const upload = multer({
  dest: "uploads/",
  limits: { fileSize: 20 * 1024 * 1024 }, // 20MB
});

/* ---------------- Swagger Setup ---------------- */

const swaggerSpec = swaggerJSDoc({
  definition: {
    openapi: "3.0.0",
    info: {
      title: "Chatbot Backend (Node.js)",
      version: "1.0.0",
      description:
        "Backend exposing /chat and /upload-pdf and forwarding requests to Python AI layer.",
    },
    servers: [{ url: `http://localhost:${NODE_PORT}` }],
  },
  apis: ["./server.js"],
});

app.use("/docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec));

/* ---------------- Health Check ---------------- */

app.get("/health", (req, res) => {
  res.json({
    ok: true,
    service: "backend-node",
    ai_base_url: AI_BASE_URL,
  });
});

/* ---------------- Chat Endpoint ---------------- */

app.post("/chat", async (req, res) => {
  try {
    const { message, history } = req.body || {};

    if (!message || typeof message !== "string") {
      return res
        .status(400)
        .json({ error: "message is required and must be a string" });
    }

    const payload = {
      message,
      history: Array.isArray(history) ? history : [],
    };

    console.log("Sending to AI:", payload);

    const aiResp = await fetch(`${AI_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await aiResp.json();

    if (!aiResp.ok) {
      return res.status(500).json({
        error: "AI layer error",
        details: data,
      });
    }

    res.json({
      reply: data.reply,
      sources: data.sources || [],
    });
  } catch (e) {
    console.error("CHAT ERROR:", e);

    res.status(500).json({
      error: "Backend failed",
      details: e.message,
    });
  }
});

/* ---------------- PDF Upload Endpoint ---------------- */

app.post("/upload-pdf", upload.single("file"), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "PDF file is required" });
    }

    console.log("Uploading file:", req.file.originalname);

    const formData = new FormData();
    formData.append(
      "file",
      fs.createReadStream(req.file.path),
      req.file.originalname
    );

    const aiResp = await fetch(`${AI_BASE_URL}/upload-pdf`, {
      method: "POST",
      body: formData,
      headers: formData.getHeaders(),
    });

    const data = await aiResp.json();

    console.log("AI response:", data);

    res.json(data);
  } catch (e) {
    console.error("UPLOAD ERROR:", e);

    res.status(500).json({
      error: "Upload failed",
      details: e.message,
    });
  }
});

/* ---------------- Start Server ---------------- */

app.listen(NODE_PORT, () => {
  console.log(`Backend running: http://localhost:${NODE_PORT}`);
  console.log(`Swagger UI: http://localhost:${NODE_PORT}/docs`);
});