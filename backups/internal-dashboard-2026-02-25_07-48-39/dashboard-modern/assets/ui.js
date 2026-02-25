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

export function RequestTrendChart({ points = [], ariaLabel = "Request trend chart" }) {
  const normalizedPoints = Array.isArray(points)
    ? points
        .map((point) => ({
          bucket: String(point?.bucket ?? ""),
          requests: Number(point?.requests ?? 0),
        }))
        .filter((point) => Number.isFinite(point.requests) && point.requests >= 0)
    : [];

  if (!normalizedPoints.length) {
    return React.createElement("p", { className: "trend-empty" }, "No request trend data available for this range.");
  }

  const chartWidth = 560;
  const chartHeight = 140;
  const padding = { top: 10, right: 12, bottom: 24, left: 10 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const barGap = 4;
  const barWidth = Math.max((plotWidth - barGap * (normalizedPoints.length - 1)) / normalizedPoints.length, 2);
  const maxRequests = Math.max(...normalizedPoints.map((point) => point.requests), 1);

  const bars = normalizedPoints.map((point, index) => {
    const scaledHeight = (point.requests / maxRequests) * plotHeight;
    const x = padding.left + index * (barWidth + barGap);
    const y = padding.top + (plotHeight - scaledHeight);

    return React.createElement("rect", {
      key: `${point.bucket}-${index}`,
      x,
      y,
      width: barWidth,
      height: Math.max(scaledHeight, 1),
      rx: 2,
      className: "trend-bar",
    });
  });

  const firstBucket = normalizedPoints[0]?.bucket ?? "";
  const lastBucket = normalizedPoints[normalizedPoints.length - 1]?.bucket ?? "";

  return React.createElement(
    "div",
    { className: "trend-chart" },
    React.createElement(
      "svg",
      {
        className: "trend-svg",
        viewBox: `0 0 ${chartWidth} ${chartHeight}`,
        role: "img",
        "aria-label": ariaLabel,
        preserveAspectRatio: "none",
      },
      React.createElement("line", {
        x1: padding.left,
        y1: chartHeight - padding.bottom,
        x2: chartWidth - padding.right,
        y2: chartHeight - padding.bottom,
        className: "trend-axis",
      }),
      bars
    ),
    React.createElement(
      "div",
      { className: "trend-labels" },
      React.createElement("span", null, firstBucket),
      React.createElement("span", null, lastBucket)
    )
  );
}

export function Notice({ tone = "info", children }) {
  return React.createElement("p", { className: `notice ${tone}` }, children);
}
