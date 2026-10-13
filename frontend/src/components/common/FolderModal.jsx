import { useState } from 'react'
import { FolderPlus, X } from 'lucide-react'

export default function FolderModal({ isOpen, onClose, onCreateFolder }) {
  const [folderName, setFolderName] = useState('')
  const [folderColor, setFolderColor] = useState('#0E6B70')

  if (!isOpen) return null

  const colors = [
    { label: 'Ocean', value: '#0E6B70' },
    { label: 'Indigo', value: '#4F46E5' },
    { label: 'Emerald', value: '#059669' },
    { label: 'Purple', value: '#7C3AED' },
    { label: 'Coral', value: '#D86E53' },
    { label: 'Amber', value: '#D97706' },
  ]

  function handleSubmit(e) {
    e.preventDefault()
    if (!folderName.trim()) return
    onCreateFolder({
      id: `f-${crypto.randomUUID()}`,
      name: folderName.trim(),
      color: folderColor,
      createdAt: Date.now(),
    })
    setFolderName('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-xs fade-up">
      <div className="relative w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-mint text-ocean">
              <FolderPlus size={18} />
            </div>
            <h3 className="font-display text-base font-bold text-ink">Create New Project / Folder</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-ink transition"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1.5">
              Project / Folder Name
            </label>
            <input
              type="text"
              autoFocus
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              placeholder="e.g. DBS Trials, Epilepsy Monotherapy..."
              className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1.5">
              Theme Color
            </label>
            <div className="flex items-center gap-2">
              {colors.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setFolderColor(c.value)}
                  className={`h-6 w-6 rounded-full transition-transform ${
                    folderColor === c.value ? 'scale-125 ring-2 ring-offset-2 ring-neutral-400' : 'hover:scale-110'
                  }`}
                  style={{ backgroundColor: c.value }}
                  title={c.label}
                />
              ))}
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-neutral-200 px-4 py-2 text-xs font-semibold text-neutral-600 hover:bg-neutral-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!folderName.trim()}
              className="rounded-xl bg-ink px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-ocean transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Create Folder
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
