import React from "https://esm.sh/react@18.3.1";

export function Shell({ title, navItems, route, onNavigate, children }) {
  return React.createElement(
    "div",
    { className: "shell" },
    React.createElement(
      "aside",
      { className: "sidebar" },
      React.createElement("div", { className: "brand" }, "Y Finance"),
      React.createElement(
        "div",
        { className: "brand-sub" },
        "Dashboard"
      ),
      React.createElement(
        "nav",
        { className: "nav" },
        navItems.map((item) =>
          React.createElement(
            "button",
            {
              key: item.key,
              className: `nav-item ${route === item.key ? "active" : ""}`,
              onClick: () => onNavigate(item.key),
              type: "button",
            },
            item.label
          )
        )
      )
    ),
    React.createElement(
      "main",
      { className: "content" },
      React.createElement(
        "header",
        { className: "content-head" },
        React.createElement("h1", null, title),
        React.createElement(
          "div",
          { className: "badge" },
          "vertical-slice"
        )
      ),
      children
    )
  );
}

export function Grid({ children }) {
  return React.createElement("section", { className: "grid" }, children);
}

export function Card({ title, value, meta, children }) {
  return React.createElement(
    "article",
    { className: "card" },
    title ? React.createElement("p", { className: "card-title" }, title) : null,
    value ? React.createElement("p", { className: "card-value" }, value) : null,
    meta ? React.createElement("p", { className: "card-meta" }, meta) : null,
    children
  );
}

export function SegmentControl({ value, options, onChange }) {
  return React.createElement(
    "div",
    { className: "segment" },
    options.map((option) =>
      React.createElement(
        "button",
        {
          key: option.value,
          type: "button",
          className: `segment-item ${value === option.value ? "active" : ""}`,
          onClick: () => onChange(option.value),
        },
        option.label
      )
    )
  );
}

export function Table({ columns, rows }) {
  return React.createElement(
    "div",
    { className: "table-wrap" },
    React.createElement(
      "table",
      { className: "table" },
      React.createElement(
        "thead",
        null,
        React.createElement(
          "tr",
          null,
          columns.map((column) => React.createElement("th", { key: column.key }, column.label))
        )
      ),
      React.createElement(
        "tbody",
        null,
        rows.length
          ? rows.map((row, rowIndex) =>
              React.createElement(
                "tr",
                { key: row.id ?? rowIndex },
                columns.map((column) => React.createElement("td", { key: column.key }, row[column.key]))
              )
            )
          : React.createElement(
              "tr",
              null,
              React.createElement(
                "td",
                { colSpan: columns.length, className: "empty" },
                "No data"
              )
            )
      )
    )
  );
}

export function FormRow({ children }) {
  return React.createElement("div", { className: "form-row" }, children);
}

export function Input(props) {
  return React.createElement("input", { ...props, className: `input ${props.className ?? ""}`.trim() });
}

export function Select(props) {
  return React.createElement("select", { ...props, className: `input ${props.className ?? ""}`.trim() });
}

export function Button({ tone = "default", ...props }) {
  return React.createElement("button", {
    ...props,
    className: `btn ${tone} ${props.className ?? ""}`.trim(),
    type: props.type ?? "button",
  });
}

export function Notice({ tone = "info", children }) {
  return React.createElement("p", { className: `notice ${tone}` }, children);
}
