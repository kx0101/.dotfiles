export function taskEntityKey(area, item) {
  return [
    "task",
    area,
    item.path ?? "",
    item.line_number ?? "",
    item.task_date ?? "",
  ].join(":");
}
