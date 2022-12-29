interface User {
  name: string;
  id: number;
}

const user: User = {
  name: 1234,
  id: "234324",
};

export const uiSchema = {
  "ui:labels": { namespace: "hello" },
  "ui:options": {
    key: "value",
  },
};
