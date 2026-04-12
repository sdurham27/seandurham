interface Props {
  level: number | null;  // 1-10
}

export function EnergyBar({ level }: Props) {
  const pips = 5; // show 5 pips representing pairs 1-2, 3-4, 5-6, 7-8, 9-10
  const filled = level ? Math.ceil(level / 2) : 0;
  return (
    <div className="energy-bar" title={level ? `Energy: ${level}/10` : "Energy unknown"}>
      {Array.from({ length: pips }).map((_, i) => (
        <div
          key={i}
          className={`energy-pip${i < filled ? (filled >= 4 ? " high" : " filled") : ""}`}
        />
      ))}
    </div>
  );
}
