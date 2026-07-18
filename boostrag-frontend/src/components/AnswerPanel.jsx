import ReactMarkdown from "react-markdown";
import { ChevronRight } from "lucide-react";
import { Panel, PanelHeader } from "./primitives";

const answerCards = [
  {
    tag: "INTAKE",
    title: "High Flow Intakes: Do They Actually Add Power?",
    copy: "Testing shows gains of 8–15 whp on the B58 with quality intakes.",
    sources: 12,
    image: "/assets/intake-card.png",
  },
  {
    tag: "EXHAUST",
    title: "Catted vs Catless Downpipes on the B58",
    copy: "Catted retains low-end torque and keeps CEL at bay.",
    sources: 18,
    image: "/assets/downpipe-card.png",
  },
  {
    tag: "COOLING",
    title: "Upgraded Intercoolers: Worth It?",
    copy: "Lower IATs equal consistent power, especially in hot climates.",
    sources: 14,
    image: "/assets/intercooler-card.png",
  },
];

export function OriginBadge({ origin, variant = "dark" }) {
  if (!origin) return null;

  const darkTones = {
    corpus: "bg-green-500/15 text-green-400",
    web: "bg-blue-500/15 text-blue-400",
    none: "bg-neutral-500/15 text-neutral-400",
  };
  const lightTones = {
    corpus: "bg-green-600/10 text-green-700",
    web: "bg-blue-600/10 text-blue-700",
    none: "bg-neutral-500/10 text-neutral-600",
  };
  const tones = variant === "light" ? lightTones : darkTones;

  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium mb-2 " +
        (tones[origin] || tones.none)
      }
    >
      {origin === "corpus"
        ? "● From your trusted corpus"
        : origin === "web"
        ? "● Live web research — less vetted"
        : "● No confident answer yet"}
    </span>
  );
}

export function SourceBackedAnswers({ answer, sources, origin, error }) {
  if (error) {
    return (
      <Panel className="p-4">
        <PanelHeader title="Source-Backed Answers" />
        <div className="border border-red-900/70 bg-red-950/20 p-5 text-sm font-semibold leading-6 text-red-200">
          {error}
        </div>
      </Panel>
    );
  }

  if (answer) {
    return (
      <Panel className="p-4">
        <PanelHeader title="BoostRAG Answer" />

        <div className="space-y-4">
          <div>
            <OriginBadge origin={origin} />
          </div>

          {origin === "none" ? (
            <p className="text-neutral-400 italic">
              BoostRAG doesn't have a confident answer for this yet.
            </p>
          ) : (
            <>
              <div className="border border-zinc-800 bg-black/50 p-5 text-[15px] font-medium leading-7 text-zinc-200">
                <ReactMarkdown
                  components={{
                    strong: ({ children }) => (
                      <strong className="font-black text-white">{children}</strong>
                    ),
                    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                    ul: ({ children }) => (
                      <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>
                    ),
                    li: ({ children }) => <li>{children}</li>,
                  }}
                >
                  {answer}
                </ReactMarkdown>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-black uppercase tracking-wide text-yellow-400">
                  Sources Used
                </h3>

                <div className="grid gap-3 xl:grid-cols-2">
                  {sources.map((source, index) => (
                    <article
                      key={`${source.source_file}-${index}`}
                      className="border border-zinc-800 bg-zinc-950/90 p-4"
                    >
                      <p className="text-[11px] font-black uppercase text-red-600">
                        {source.category || "Source"}
                        {source.trust_tier && (
                          <span className="ml-2 rounded bg-neutral-700/50 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-neutral-300">
                            {source.trust_tier}
                          </span>
                        )}
                      </p>

                      <h4 className="mt-1 text-[15px] font-black leading-5 text-white">
                        {source.product || source.source_file || "Unknown source"}
                      </h4>

                      <p className="mt-2 text-[12px] font-semibold text-zinc-500">
                        {source.brand || "Unknown brand"}
                        {source.price ? ` • ${source.price}` : ""}
                      </p>

                      {source.text_preview && (
                        <p className="mt-3 line-clamp-3 text-[12px] leading-5 text-zinc-400">
                          {source.text_preview}
                        </p>
                      )}

                      {source.url && (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-3 inline-block text-[12px] font-black uppercase text-yellow-400 hover:text-yellow-300"
                        >
                          View Source
                        </a>
                      )}
                    </article>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </Panel>
    );
  }

  return (
    <Panel className="p-4">
      <PanelHeader title="Source-Backed Answers" />

      <div className="grid gap-3 xl:grid-cols-3">
        {answerCards.map((card) => (
          <article
            key={card.title}
            className="group relative grid min-h-[185px] grid-cols-[130px_1fr] overflow-hidden border border-zinc-800 bg-zinc-950/90 transition hover:border-red-700"
          >
            <div className="relative overflow-hidden bg-black">
              <img
                src={card.image}
                alt={card.title}
                className="h-full w-full object-cover opacity-90 grayscale-[25%] transition duration-500 group-hover:scale-110 group-hover:grayscale-0"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-transparent to-black/45" />
            </div>

            <div className="flex flex-col p-4">
              <p className="text-[11px] font-black uppercase text-red-600">
                {card.tag}
              </p>

              <h3 className="mt-1 text-[16px] font-black leading-5 text-white">
                {card.title}
              </h3>

              <p className="mt-3 flex-1 text-[13px] font-medium leading-5 text-zinc-400">
                {card.copy}
              </p>

              <div className="mt-3 flex items-center justify-between text-[12px] font-bold text-zinc-500">
                <span>Sources: {card.sources}</span>
                <ChevronRight
                  size={18}
                  className="transition group-hover:translate-x-1 group-hover:text-red-500"
                />
              </div>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}
