// scripts/seed-users.js - Python auto-generated
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const bcrypt = require('bcryptjs');

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'your_encryption_key_32chars';
const FK_ORDER = ["categories", "platform_daily_stats", "users", "merchants", "operation_logs", "orders", "refresh_tokens", "user_addresses", "merchant_daily_stats", "merchant_wallets", "reconciliation_statements", "settlement_orders", "shops", "withdrawal_requests", "spu", "sub_orders", "order_items", "payments", "product_images", "refund_requests", "shipments", "sku", "cart_items", "inventories", "refund_logs", "shipment_events"];

function findSeedFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const f of fs.readdirSync(dir)) {
    if (f.endsWith('.json')) results.push(path.join(dir, f));
  }
  results.sort((a, b) => {
    const na = path.basename(a, '.json'), nb = path.basename(b, '.json');
    return (FK_ORDER.indexOf(na) === -1 ? 99 : FK_ORDER.indexOf(na)) -
           (FK_ORDER.indexOf(nb) === -1 ? 99 : FK_ORDER.indexOf(nb));
  });
  return results;
}

async function main() {
  const dbHost = process.env.DB_HOST || 'localhost';
  const dbPort = parseInt(process.env.DB_PORT) || 3306;
  const dbUser = process.env.DB_USER || 'root';
  const dbPassword = process.env.DB_PASSWORD || '';
  const dbName = process.env.DB_NAME || 'testdb';

  const conn = await mysql.createConnection({ host: dbHost, port: dbPort, user: dbUser, password: dbPassword, database: dbName });
  const seedDir = path.join(__dirname, '..', 'database', 'seed');
  if (!fs.existsSync(seedDir)) { console.log('[seed] database/seed/ not found'); await conn.end(); return; }
  const files = findSeedFiles(seedDir);
  if (!files.length) { console.log('[seed] No seed files'); await conn.end(); return; }

  console.log('[seed] ' + files.length + ' files (FK order)');
  await conn.query('SET FOREIGN_KEY_CHECKS=0');
  let ok = 0, fail = 0, totalRows = 0;
  const failedTables = [];
  const skippedTables = [];

  for (const fp of files) {
    const fileName = path.basename(fp, '.json');

    // 预检查：文件名对应的表是否存在（快速跳过无关文件）
    const [t] = await conn.query(
      'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME=?',
      [dbName, fileName]
    );
    if (!t.length) {
      console.log('  - ' + fileName + ': table not found, skip');
      skippedTables.push(fileName + ' (表不存在)');
      continue;
    }

    let raw;
    try { raw = JSON.parse(fs.readFileSync(fp, "utf8")); }
    catch (e) {
      console.error("  FAIL " + fileName + ": JSON parse error — " + e.message);
      failedTables.push(fileName + ' (JSON解析失败)');
      fail++; continue;
    }

    // 兼容三种格式:
    //   A. 裸数组 [...] → 以文件名为表名
    //   B. 单表包装 {"users": [...]} → 以 key 为表名（key 与文件名一致）
    //   C. 多表包装 {"users": [...], "user_profiles": [...]} → 遍历所有 key，各插各表（容错）
    let tableGroups = []; // [{tableName, rows}]
    if (Array.isArray(raw)) {
      tableGroups.push({ tableName: fileName, rows: raw });
    } else if (typeof raw === "object" && raw !== null) {
      const keys = Object.keys(raw);
      const arrKeys = keys.filter(k => Array.isArray(raw[k]) && raw[k].length > 0);
      if (arrKeys.length === 0) {
        console.log("  - " + fileName + ": 无有效数据数组，skip");
        skippedTables.push(fileName + ' (无有效数据)');
        continue;
      }
      for (const k of arrKeys) {
        tableGroups.push({ tableName: k, rows: raw[k] });
      }
    } else {
      console.log("  - " + fileName + ": 格式不支持，skip");
      skippedTables.push(fileName + ' (格式不支持)');
      continue;
    }

    for (const group of tableGroups) {
      const tbl = group.tableName;
      const rows = group.rows;
      // 跳过已通过预检查的表（fileName 对应的表）
      if (tbl !== fileName) {
        const [tt] = await conn.query(
          'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME=?',
          [dbName, tbl]
        );
        if (!tt.length) {
          console.log("  - " + tbl + ": table not found, skip (from " + fileName + ".json)");
          skippedTables.push(tbl + ' (表不存在，来自 ' + fileName + '.json)');
          continue;
        }
      }

      // 🛑 查询 MySQL 实际列名，冲突时以数据库为准（过滤 seed 多余列）
      const [colInfo] = await conn.query(
        'SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=?',
        [dbName, tbl]
      );
      const actualCols = new Set(colInfo.map(r => r.COLUMN_NAME));
      const seedCols = Object.keys(rows[0] || {});
      const extraSeedCols = seedCols.filter(c => !actualCols.has(c));
      const missingSeedCols = [...actualCols].filter(c => !seedCols.includes(c) && !['created_at','updated_at'].includes(c));

      if (extraSeedCols.length > 0) {
        console.log('  [warn] ' + tbl + ': seed 多余列（以数据库为准，自动忽略）: ' + extraSeedCols.join(', '));
      }
      if (missingSeedCols.length > 0) {
        console.log('  [warn] ' + tbl + ': seed 缺列（数据库有但 seed 无）: ' + missingSeedCols.join(', '));
      }

      let inserted = 0, rowFails = 0;
      for (const row of rows) {
        for (const [k, v] of Object.entries(row)) {
          if (typeof v === "string") {
            if (v.startsWith("{{bcrypt:") && v.endsWith("}}"))
              row[k] = await bcrypt.hash(v.slice(9, -2), 10);
            else if (v.startsWith("{{aes:") && v.endsWith("}}"))
              row[k] = v.slice(6, -2);
          }
        }
        // 🛑 过滤多余列：只插入数据库中实际存在的列
        const cols = Object.keys(row).filter(c => actualCols.has(c));
        const escapedKey = ENCRYPTION_KEY.replace(/'/g, "\\'");
        const placeholders = cols.map(c => {
          if (c === "phone") return "AES_ENCRYPT(?, '" + escapedKey + "')";
          return '?';
        }).join(', ');
        try {
          await conn.query(
            'INSERT IGNORE INTO `' + tbl + '` (' + cols.map(c => '`' + c + '`').join(', ') + ') VALUES (' + placeholders + ')',
            Object.values(row)
          );
          inserted++;
        } catch (e) {
          console.error('  FAIL ' + tbl + ' INSERT row[' + rowFails + ']: ' + e.message);
          rowFails++;
        }
      }

      if (rowFails > 0) {
        fail += rowFails;
        failedTables.push(tbl + ' (' + inserted + '/' + rows.length + ' rows, ' + rowFails + ' failed)');
      }
      if (inserted > 0) {
        console.log("  OK " + tbl + ": " + inserted + "/" + rows.length + " rows" + (rowFails > 0 ? ' (' + rowFails + ' failed)' : ''));
        ok++; totalRows += inserted;
      } else if (rowFails === 0) {
        console.log("  - " + tbl + ": 0 rows inserted (seed 数据为空)");
        skippedTables.push(tbl + ' (0行数据)');
      }
    }
  }
  await conn.query('SET FOREIGN_KEY_CHECKS=1');
  await conn.end();

  // 🛑 汇总：打印成功/跳过/失败清单
  console.log('');
  console.log('[seed] Files:' + ok + ' Rows:' + totalRows + ' Failed:' + fail + ' Skipped:' + skippedTables.length);
  if (skippedTables.length > 0) {
    console.log('[seed] ⚠️ 以下 ' + skippedTables.length + ' 个表被跳过（数据未插入）:');
    skippedTables.forEach(t => console.log('  ⚠️ ' + t));
  }
  if (failedTables.length > 0) {
    console.log('[seed] ❌ 以下 ' + failedTables.length + ' 个表种子数据插入失败:');
    failedTables.forEach(t => console.log('  ❌ ' + t));
    process.exit(1);
  } else if (skippedTables.length > 0) {
    console.log('[seed] ⚠️ 部分表被跳过，但不影响已插入的数据');
  } else {
    console.log('[seed] ✅ 全部种子数据插入成功');
  }
}

main().catch(e => { console.error('[seed] Fatal:', e.message); process.exit(1); });
