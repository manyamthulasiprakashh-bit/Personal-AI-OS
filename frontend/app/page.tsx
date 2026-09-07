import { AuthControls } from "./components/auth-controls";

const stats = [
  { label: "Tasks completed", value: "0" },
  { label: "Study time", value: "0h" },
  { label: "Job applications", value: "0" },
  { label: "Learning progress", value: "0%" },
];

const activities = [
  { agent: "Routine Agent", status: "completed" },
  { agent: "Learning Agent", status: "analyzing skill gaps" },
  { agent: "Job Agent", status: "5 jobs analyzed" },
  { agent: "Stock Agent", status: "market report generated" },
];

export default function HomePage() {
  return (
    <main className="min-h-screen p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex items-center justify-between rounded-2xl border border-slate-700 bg-slate-900/60 p-6 shadow-xl">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-sky-400">Personal AI-OS</p>
            <h1 className="mt-2 text-3xl font-bold text-white">Dashboard</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
              System status: online
            </div>
            <AuthControls />
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-2xl border border-slate-700 bg-slate-900/60 p-5">
              <div className="text-sm text-slate-300">{stat.label} (preview)</div>
              <div className="mt-3 text-3xl font-bold text-white">{stat.value}</div>
            </div>
          ))}
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[2fr_1fr]">
          <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-xl font-semibold text-white">Today (preview)</h2>
            <ul className="space-y-3 text-slate-200">
              <li>• Review and plan the day with the routine agent.</li>
              <li>• Focus on the highest-priority learning objective.</li>
              <li>• Track job opportunities with explicit human approval for follow-through.</li>
              <li>• Review watchlist signals without triggering any trade actions.</li>
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-xl font-semibold text-white">Agent Activity (preview)</h2>
            <div className="space-y-3">
              {activities.map(({ agent, status }) => (
                <div key={agent} className="flex items-center justify-between rounded-xl bg-slate-800/80 p-3">
                  <span className="text-slate-200">{agent}</span>
                  <span className="text-sm text-sky-300">{status}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
