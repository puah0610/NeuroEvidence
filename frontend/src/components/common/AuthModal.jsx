import { useState } from 'react'
import { AlertCircle, Brain, Eye, EyeOff, Lock, LogIn, Mail, User, UserPlus } from 'lucide-react'
import { api } from '../../api'
import { authenticateUser as authenticateLocalFallback } from '../../utils/sessionStore'

export default function AuthModal({ isOpen, onLogin }) {
  const [authMode, setAuthMode] = useState('login') // 'login' | 'register'
  const [identifier, setIdentifier] = useState('')
  const [fullName, setFullName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!isOpen) return null

  function switchMode(nextMode) {
    setAuthMode(nextMode)
    setError('')
    setPassword('')
    setConfirmPassword('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (authMode === 'register') {
      if (password !== confirmPassword) {
        setError('Passwords do not match.')
        return
      }
      if (password.trim().length < 4) {
        setError('Password must be at least 4 characters.')
        return
      }

      setSubmitting(true)
      try {
        const res = await api.register({
          username: username.trim(),
          email: email.trim(),
          password,
          full_name: fullName.trim() || username.trim(),
        })
        setFullName('')
        setUsername('')
        setEmail('')
        setPassword('')
        setConfirmPassword('')
        setAuthMode('login')
        onLogin({
          userId: res.user_id,
          accountRole: res.account_role,
          profile: res.profile,
        })
      } catch (err) {
        const detail =
          err.response?.data?.detail ||
          (Array.isArray(err.response?.data?.detail)
            ? err.response.data.detail[0]?.msg
            : null) ||
          'Could not create account. Please ensure the backend API is running.'
        setError(typeof detail === 'string' ? detail : 'Registration failed.')
      } finally {
        setSubmitting(false)
      }
      return
    }

    // Sign In
    setSubmitting(true)
    try {
      const res = await api.login({ identifier: identifier.trim(), password })
      setIdentifier('')
      setPassword('')
      onLogin({
        userId: res.user_id,
        accountRole: res.account_role,
        profile: res.profile,
      })
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Invalid username or password.')
      } else {
        // Offline fallback if backend is unreachable
        const fallback = authenticateLocalFallback({ identifier, password })
        if (fallback.ok) {
          setIdentifier('')
          setPassword('')
          onLogin({
            userId: fallback.userId,
            accountRole: fallback.accountRole,
            profile: fallback.profile,
          })
        } else {
          setError(
            err.response?.data?.detail ||
              'Could not reach authentication server. Please check backend status.'
          )
        }
      }
    } finally {
      setSubmitting(false)
    }
  }

  const isRegister = authMode === 'register'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-4 backdrop-blur-md fade-up">
      <div className="relative w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-ink text-white shadow-md">
            <Brain size={26} strokeWidth={2} />
          </div>
          <h2 className="font-display text-xl font-bold text-ink">
            {isRegister ? 'Create Account' : 'NeuroEvidence'}
          </h2>
          <p className="mt-1 text-xs text-neutral-500">
            {isRegister
              ? 'Register a new clinician account with private session storage'
              : 'Sign in to access evidence-verified neurological literature support'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          {isRegister ? (
            <>
              <div>
                <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User
                    size={14}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
                  />
                  <input
                    type="text"
                    autoFocus
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Dr. Alex Tan"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 pl-9 pr-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
                  Username
                </label>
                <div className="relative">
                  <User
                    size={14}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
                  />
                  <input
                    type="text"
                    required
                    minLength={2}
                    maxLength={40}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. alex_tan"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 pl-9 pr-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail
                    size={14}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
                  />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="alex@hospital.edu"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 pl-9 pr-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>
              </div>
            </>
          ) : (
            <div>
              <label className="block text-[11px] font-semibold text-neutral-700 mb-1.5">
                Username or Email Address
              </label>
              <div className="relative">
                <User
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
                />
                <input
                  type="text"
                  autoFocus
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="Enter username or email"
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 pl-9 pr-3 py-2.5 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock
                size={14}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
              />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={isRegister ? 4 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isRegister ? 'Create a password (min 4 chars)' : 'Enter password'}
                className="w-full rounded-xl border border-neutral-200 bg-neutral-50 pl-9 pr-9 py-2.5 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-ink transition"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          {isRegister && (
            <div>
              <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
                Confirm Password
              </label>
              <div className="relative">
                <Lock
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
                />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 pl-9 pr-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-2.5 text-[11px] font-medium text-red-700">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-ocean transition disabled:opacity-50"
          >
            {isRegister ? <UserPlus size={15} /> : <LogIn size={15} />}
            <span>
              {submitting
                ? isRegister
                  ? 'Creating account...'
                  : 'Signing in...'
                : isRegister
                ? 'Create Account'
                : 'Sign In'}
            </span>
          </button>

          <div className="pt-1 text-center text-xs text-neutral-500">
            {isRegister ? (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="font-semibold text-ocean hover:underline"
                >
                  Sign in
                </button>
              </>
            ) : (
              <>
                New to NeuroEvidence?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('register')}
                  className="font-semibold text-ocean hover:underline"
                >
                  Create an account
                </button>
              </>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
