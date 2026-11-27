export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-14 space-y-4 text-sm text-gray-300">
      <h1 className="text-3xl font-extrabold text-white">About MaanCamera</h1>
      <p>
        MaanCamera is India&apos;s open-source-first marketplace and studio SaaS connecting clients with verified photography and videography teams.
      </p>
      <p className="text-xs text-gray-400">
        Built with FastAPI, PostgreSQL 16 + pgvector + Row-Level Security, Valkey, SeaweedFS S3, Ollama, and Next.js.
      </p>
    </div>
  );
}
