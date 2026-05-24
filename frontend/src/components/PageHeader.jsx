export default function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex items-start justify-between px-8 pt-8 pb-6 border-b border-surface-border">
      <div>
        <h1 className="text-xl font-semibold text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-3">{children}</div>}
    </div>
  );
}
