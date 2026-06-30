import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'

const components: Components = {
  h1: ({ children }) => (
    <h1 className="text-2xl font-bold mt-6 mb-3 text-foreground border-b border-border pb-3 first:mt-0 tracking-tight">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold mt-5 mb-2 text-foreground">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold mt-3 mb-1.5 text-foreground/90">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-sm text-foreground/85 leading-relaxed mb-2 last:mb-0 text-justify">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-4 space-y-0.5 mb-2 text-sm text-foreground/85">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-4 space-y-0.5 mb-2 text-sm text-foreground/85">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="text-foreground/85 leading-relaxed text-justify">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  em: ({ children }) => <em className="italic text-foreground/80">{children}</em>,
  hr: () => <hr className="border-border my-4" />,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-primary/40 pl-3 my-2 text-sm text-foreground/70 italic">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead>{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr className="border-b border-border">{children}</tr>,
  th: ({ children }) => (
    <th className="text-left px-3 py-2 bg-muted font-semibold text-foreground text-xs uppercase tracking-wide border border-border">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-1.5 border border-border/50 text-foreground/80">{children}</td>
  ),
  code: ({ children, className }) => {
    const isBlock = className?.includes('language-')
    if (isBlock) {
      return (
        <code className="block bg-muted rounded p-3 text-xs font-mono overflow-x-auto my-2">
          {children}
        </code>
      )
    }
    return (
      <code className="bg-muted rounded px-1 py-0.5 text-xs font-mono text-foreground">
        {children}
      </code>
    )
  },
}

interface Props {
  children: string
  className?: string
}

export function MarkdownContent({ children, className }: Props) {
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
