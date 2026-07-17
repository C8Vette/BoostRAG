import { Gauge, Flag, ShieldCheck, TrendingUp } from "lucide-react";

export function FooterStrip() {
  const items = [
    {
      icon: <Gauge size={52} />,
      title: "Unlock Real Performance",
      text: "Data-driven insights. Real-world results.",
    },
    {
      icon: <Flag size={52} />,
      title: "Research With Confidence",
      text: "Every answer backed by credible sources.",
    },
    {
      icon: <ShieldCheck size={52} />,
      title: "Build The Right Way",
      text: "Reduce guesswork. Maximize results.",
    },
    {
      icon: <TrendingUp size={52} />,
      title: "Drive Different",
      text: "Your car. Your build. Your advantage.",
    },
  ];

  return (
    <section className="relative z-10 mx-auto grid max-w-[1350px] gap-8 px-5 pb-10 pt-6 md:grid-cols-2 lg:grid-cols-4 lg:px-10">
      {items.map((item) => (
        <div
          key={item.title}
          className="flex items-center gap-4 border-r border-zinc-900/90 pr-6"
        >
          <div className="text-red-600 drop-shadow-[0_0_16px_rgba(220,38,38,.4)]">
            {item.icon}
          </div>

          <div>
            <h3 className="text-[13px] font-black uppercase text-yellow-400">
              {item.title}
            </h3>
            <p className="mt-1 text-[14px] font-semibold leading-5 text-zinc-400">
              {item.text}
            </p>
          </div>
        </div>
      ))}
    </section>
  );
}
