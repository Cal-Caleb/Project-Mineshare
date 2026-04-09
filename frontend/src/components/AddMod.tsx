import { useState } from "react";
import { motion } from "framer-motion";
import { previewCurseForge, addCurseForgeMod, uploadModJar } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import type { CurseForgePreview } from "../lib/types";

const card = "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-6";

export default function AddMod() {
  const [tab, setTab] = useState<"curseforge" | "upload">("curseforge");

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <h1 className="font-serif text-3xl text-gold-light">Add New Mod</h1>

      {/* Tabs */}
      <div className="flex border-b border-white/10">
        <button
          onClick={() => setTab("curseforge")}
          className={`px-5 py-2.5 font-mono text-sm transition ${
            tab === "curseforge"
              ? "border-b-2 border-gold text-gold"
              : "text-white/40 hover:text-white/70"
          }`}
        >
          From CurseForge
        </button>
        <button
          onClick={() => setTab("upload")}
          className={`px-5 py-2.5 font-mono text-sm transition ${
            tab === "upload"
              ? "border-b-2 border-gold text-gold"
              : "text-white/40 hover:text-white/70"
          }`}
        >
          Upload .jar
        </button>
      </div>

      {tab === "curseforge" ? <CurseForgeTab /> : <UploadTab />}
    </motion.div>
  );
}

function CurseForgeTab() {
  const { isAdmin } = useAuth();
  const [url, setUrl] = useState("");
  const [preview, setPreview] = useState<CurseForgePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handlePreview = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setPreview(null);
    setSuccess("");
    setLoading(true);
    try {
      const data = await previewCurseForge(url);
      setPreview(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (force: boolean) => {
    setAdding(true);
    setError("");
    try {
      const mod = await addCurseForgeMod(url, force);
      setSuccess(
        mod.status === "active"
          ? `"${mod.name}" added to the server!`
          : `"${mod.name}" submitted for voting.`
      );
      setPreview(null);
      setUrl("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className={card}>
      <form onSubmit={handlePreview} className="space-y-4">
        <div>
          <label className="block font-mono text-xs text-white/50 mb-1.5">
            CurseForge URL
          </label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-space-dark px-4 py-2.5 font-mono text-sm text-white placeholder:text-white/20 focus:border-gold/30 focus:outline-none"
            placeholder="https://www.curseforge.com/minecraft/mc-mods/sodium"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-gold/20 px-5 py-2 font-mono text-sm text-gold transition hover:bg-gold/30 disabled:opacity-40"
        >
          {loading ? "Resolving..." : "Preview"}
        </button>
      </form>

      {error && <p className="mt-4 font-mono text-xs text-red-400">{error}</p>}
      {success && <p className="mt-4 font-mono text-xs text-emerald-400">{success}</p>}

      {preview && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mt-6 rounded-lg border border-gold/10 bg-space-dark/50 p-5"
        >
          <div className="flex gap-4">
            {preview.logo_url && (
              <img
                src={preview.logo_url}
                alt=""
                className="h-16 w-16 rounded-lg object-cover"
              />
            )}
            <div className="flex-1 min-w-0">
              <h3 className="font-serif text-lg text-white">{preview.name}</h3>
              <p className="font-mono text-xs text-white/40">by {preview.author}</p>
              <p className="mt-2 font-mono text-xs text-white/50 line-clamp-2">
                {preview.summary}
              </p>
              <div className="mt-2 flex gap-4 font-mono text-[10px] text-white/30">
                <span>{preview.download_count.toLocaleString()} downloads</span>
                <span>{preview.latest_file_name}</span>
              </div>
            </div>
          </div>

          <div className="mt-4 flex gap-3">
            <button
              onClick={() => handleAdd(false)}
              disabled={adding}
              className="rounded-lg bg-gold/20 px-5 py-2 font-mono text-sm text-gold transition hover:bg-gold/30 disabled:opacity-40"
            >
              {adding ? "Adding..." : "Add (starts vote)"}
            </button>
            {isAdmin && (
              <button
                onClick={() => handleAdd(true)}
                disabled={adding}
                className="rounded-lg border border-gold/20 px-5 py-2 font-mono text-sm text-gold/70 transition hover:bg-gold/10 disabled:opacity-40"
              >
                Force Add
              </button>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}

function UploadTab() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".jar")) {
      setError("Only .jar files are accepted");
      return;
    }
    setFile(f);
    setError("");
    setSuccess("");
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setError("");

    // Simulate progress since fetch doesn't support upload progress natively
    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 15, 90));
    }, 300);

    try {
      await uploadModJar(file);
      clearInterval(progressInterval);
      setProgress(100);
      setSuccess("Upload complete! Awaiting admin approval.");
      setFile(null);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={card}>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files[0];
          if (f) handleFile(f);
        }}
        className={`rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragOver
            ? "border-gold/60 bg-gold/5"
            : "border-white/10 hover:border-white/20"
        }`}
      >
        <div className="mx-auto mb-3 h-10 w-10 text-white/20">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>
        <p className="font-mono text-sm text-white/40">
          Drag & drop your .jar file here
        </p>
        <p className="my-2 font-mono text-xs text-white/20">or</p>
        <label className="inline-block cursor-pointer rounded-lg bg-gold/20 px-4 py-2 font-mono text-sm text-gold transition hover:bg-gold/30">
          Browse Files
          <input
            type="file"
            accept=".jar"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            className="hidden"
          />
        </label>
      </div>

      {file && (
        <p className="mt-3 font-mono text-xs text-white/50">
          Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
        </p>
      )}

      {uploading && (
        <div className="mt-4">
          <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
            <motion.div
              className="h-full bg-gold"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <p className="mt-1 text-center font-mono text-xs text-white/30">
            {progress}%
          </p>
        </div>
      )}

      {error && <p className="mt-3 font-mono text-xs text-red-400">{error}</p>}
      {success && <p className="mt-3 font-mono text-xs text-emerald-400">{success}</p>}

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="mt-4 w-full rounded-lg bg-gold/20 py-2.5 font-mono text-sm text-gold transition hover:bg-gold/30 disabled:opacity-40"
      >
        {uploading ? "Uploading..." : "Upload Mod"}
      </button>

      <div className="mt-6 rounded-lg border border-white/5 bg-space-dark/30 p-4">
        <h3 className="font-mono text-xs text-white/50 uppercase tracking-wider mb-2">
          Upload Guidelines
        </h3>
        <ul className="space-y-1 font-mono text-xs text-white/30 list-disc pl-4">
          <li>Only .jar files are accepted</li>
          <li>Files are quarantined and virus-scanned automatically</li>
          <li>An admin must approve before the mod goes live</li>
          <li>Max file size: 50 MB</li>
        </ul>
      </div>
    </div>
  );
}
