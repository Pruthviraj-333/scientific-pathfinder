import { Loader } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingSpinner({ message = 'Loading...', size = 'md' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-6 w-6',
    md: 'h-12 w-12',
    lg: 'h-16 w-16',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className={`animate-spin border-4 border-blue-500 border-t-transparent rounded-full ${sizeClasses[size]}`} />
      {message && (
        <p className="mt-4 text-slate-400 text-sm">{message}</p>
      )}
    </div>
  );
}

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      {icon && (
        <div className="mb-4 text-slate-500 opacity-50">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      {description && (
        <p className="text-slate-400 text-sm mb-6 max-w-md">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Stats Cards Skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-slate-800/50 rounded-xl p-6 h-32">
            <div className="h-8 w-8 bg-slate-700 rounded mb-3" />
            <div className="h-8 w-16 bg-slate-700 rounded mb-2" />
            <div className="h-4 w-24 bg-slate-700 rounded" />
          </div>
        ))}
      </div>

      {/* Hypothesis Skeleton */}
      <div className="bg-slate-800/50 rounded-2xl p-8">
        <div className="h-8 w-64 bg-slate-700 rounded mb-4" />
        <div className="space-y-2">
          <div className="h-4 bg-slate-700 rounded w-full" />
          <div className="h-4 bg-slate-700 rounded w-5/6" />
          <div className="h-4 bg-slate-700 rounded w-4/6" />
        </div>
      </div>

      {/* Graph Stats Skeleton */}
      <div className="bg-slate-800/50 rounded-2xl p-8">
        <div className="h-6 w-48 bg-slate-700 rounded mb-4" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-6 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    </div>
  );
}