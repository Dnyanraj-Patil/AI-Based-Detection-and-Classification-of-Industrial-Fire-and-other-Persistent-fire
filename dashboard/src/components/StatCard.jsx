export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "",
}) {
  return (
    <div className={`stat-card ${variant}`}>
      <div className="stat-card-header">
        <span>{title}</span>

        {Icon && (
          <div className="stat-icon">
            <Icon size={18} />
          </div>
        )}
      </div>

      <div className="stat-value">
        {value}
      </div>

      {subtitle && (
        <div className="stat-subtitle">
          {subtitle}
        </div>
      )}
    </div>
  );
}