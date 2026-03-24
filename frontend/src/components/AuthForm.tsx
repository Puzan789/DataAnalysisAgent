import { useState } from 'react'
import { Loader2, Lock, Mail, User as UserIcon } from 'lucide-react'

interface AuthFormProps {
  onLogin: (email: string, password: string) => Promise<void>
  onSignup: (email: string, password: string, name?: string) => Promise<void>
}

export default function AuthForm({ onLogin, onSignup }: AuthFormProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === 'login') {
        await onLogin(email, password)
      } else {
        await onSignup(email, password, name)
      }
    } catch (err) {
      setError((err as Error).message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-0">
      <div className="w-full max-w-md bg-surface-1 border border-zinc-800 rounded-2xl p-8 shadow-xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-brand flex items-center justify-center text-white">
            <Lock size={18} />
          </div>
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-[0.2em]">Data Agent</p>
            <h1 className="text-lg font-semibold text-zinc-100">{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
          </div>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <label className="block text-sm text-zinc-400">
              <span className="text-xs text-zinc-500">Name</span>
              <div className="mt-1 flex items-center gap-2 bg-surface-2 border border-zinc-800 rounded-lg px-3 py-2">
                <UserIcon size={14} className="text-zinc-500" />
                <input
                  className="bg-transparent flex-1 text-sm outline-none text-zinc-100"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </label>
          )}

          <label className="block text-sm text-zinc-400">
            <span className="text-xs text-zinc-500">Email</span>
            <div className="mt-1 flex items-center gap-2 bg-surface-2 border border-zinc-800 rounded-lg px-3 py-2">
              <Mail size={14} className="text-zinc-500" />
              <input
                className="bg-transparent flex-1 text-sm outline-none text-zinc-100"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </label>

          <label className="block text-sm text-zinc-400">
            <span className="text-xs text-zinc-500">Password</span>
            <div className="mt-1 flex items-center gap-2 bg-surface-2 border border-zinc-800 rounded-lg px-3 py-2">
              <Lock size={14} className="text-zinc-500" />
              <input
                className="bg-transparent flex-1 text-sm outline-none text-zinc-100"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </label>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            type="submit"
            className="w-full py-2.5 rounded-lg bg-brand text-white text-sm font-medium hover:bg-brand-light transition disabled:opacity-60"
            disabled={loading}
          >
            {loading ? <Loader2 size={16} className="animate-spin mx-auto" /> : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <div className="mt-4 text-center text-xs text-zinc-500">
          {mode === 'login' ? (
            <button className="text-brand-light hover:underline" onClick={() => setMode('signup')}>
              Need an account? Sign up
            </button>
          ) : (
            <button className="text-brand-light hover:underline" onClick={() => setMode('login')}>
              Already have an account? Sign in
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
