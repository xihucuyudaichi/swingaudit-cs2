import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const components = {
  a: ({ children, href }) => href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>,
  img: ({ alt }) => <span>{alt || '图片'}</span>,
  table: ({ children }) => <div className="answer-table-scroll" tabIndex={0} role="region" aria-label="回答中的数据表格，可左右滚动"><table>{children}</table></div>
};
export default function AnswerMarkdown({ text }) {
  return <div className="answer-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={components}>{text || ''}</Markdown></div>;
}
