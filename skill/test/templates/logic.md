# logic 层测试模板 — jest (CJS)

```js
jest.mock('../../config/db', () => ({
  query: jest.fn(), beginTransaction: jest.fn(), commit: jest.fn(), rollback: jest.fn()
}));
const service = require('../../services/xxxService');

describe('logic: steps + transaction + errorMapping', () => {
  beforeEach(() => { jest.clearAllMocks(); });
  const db = require('../../config/db');

  it('step order: beginTransaction -> lock -> insert -> commit', async () => {
    db.query.mockResolvedValue([{ insertId: 1 }]);
    await service.create();
    expect(db.beginTransaction).toHaveBeenCalled();
    expect(db.query).toHaveBeenNthCalledWith(1, expect.stringContaining('FOR UPDATE'), expect.any(Array));
    expect(db.query).toHaveBeenNthCalledWith(2, expect.stringContaining('INSERT'), expect.any(Array));
    expect(db.commit).toHaveBeenCalled();
  });

  it('error -> rollback + throw ERROR_CODE (align errorMapping)', async () => {
    db.query.mockRejectedValue(new Error('stock_check_failed'));
    await expect(service.create()).rejects.toThrow('INSUFFICIENT_STOCK');
    expect(db.rollback).toHaveBeenCalled();
    expect(db.commit).not.toHaveBeenCalled();
  });

  it('optimistic lock conflict -> VERSION_CONFLICT', async () => {
    db.query.mockResolvedValue([{ affectedRows: 0 }]);
    await expect(service.confirm()).rejects.toThrow('VERSION_CONFLICT');
  });
});
```
