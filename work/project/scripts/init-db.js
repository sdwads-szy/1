// scripts/init-db.js - Python auto-generated
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

const FK_ORDER = ["categories", "platform_daily_stats", "users", "merchants", "operation_logs", "orders", "refresh_tokens", "user_addresses", "merchant_daily_stats", "merchant_wallets", "reconciliation_statements", "settlement_orders", "shops", "withdrawal_requests", "spu", "sub_orders", "order_items", "payments", "product_images", "refund_requests", "shipments", "sku", "cart_items", "inventories", "refund_logs", "shipment_events"];

function findSqlFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fp = path.join(dir, entry.name);
    if (entry.isDirectory()) results.push(...findSqlFiles(fp));
    else if (entry.name.endsWith('.sql')) results.push(fp);
  }
  return results;
}

// 🛑 自检：扫描所有 SQL 文件，发现硬错误则拒绝继续（在 DROP DATABASE 之前执行）
function validateSqlFiles(files) {
  const errors = [];
  for (const fp of files) {
    let content;
    try { content = fs.readFileSync(fp, 'utf8'); }
    catch (e) { errors.push(path.basename(fp) + ': 无法读取 — ' + e.message); continue; }
    const rel = path.basename(fp);

    // 括号配对
    let depth = 0;
    for (let i = 0; i < content.length; i++) {
      if (content[i] === '(') depth++;
      else if (content[i] === ')') depth--;
      if (depth < 0) { errors.push(rel + ': 括号不配对'); depth = 0; }
    }
    if (depth > 0) errors.push(rel + ': 括号未闭合（多了 ' + depth + ' 个 (）');

    // 每个 CREATE TABLE 检查重复索引/列名
    const ctRegex = /CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\(([\s\S]*?)\)\s*ENGINE/gi;
    let ctm;
    while ((ctm = ctRegex.exec(content)) !== null) {
      const tblName = ctm[1];
      const body = ctm[2];

      // 重复索引/约束名
      const idxNames = [];
      const idxRegex = /(?:UNIQUE\s+)?(?:KEY|INDEX)\s+`(\w+)`/gi;
      let im;
      while ((im = idxRegex.exec(body)) !== null) idxNames.push(im[1]);
      const conRegex = /CONSTRAINT\s+`(\w+)`/gi;
      while ((im = conRegex.exec(body)) !== null) idxNames.push(im[1]);
      const seenIdx = new Set();
      for (const n of idxNames) {
        if (seenIdx.has(n)) errors.push(rel + ': 表 ' + tblName + ' 重复索引/约束名 `' + n + '` — MySQL 会拒绝建表');
        seenIdx.add(n);
      }

      // 重复列名
      const colNames = [];
      const colRegex = /`(\w+)`\s+\w+/gi;
      let cm;
      while ((cm = colRegex.exec(body)) !== null) colNames.push(cm[1]);
      const seenCol = new Set();
      for (const cn of colNames) {
        if (seenCol.has(cn)) errors.push(rel + ': 表 ' + tblName + ' 重复列名 `' + cn + '`');
        seenCol.add(cn);
      }

      // AUTO_INCREMENT 列必须有 PRIMARY KEY
      if (/AUTO_INCREMENT/i.test(body) && !/PRIMARY\s+KEY/i.test(body)) {
        errors.push(rel + ': 表 ' + tblName + ' AUTO_INCREMENT 列缺少 PRIMARY KEY — MySQL 会拒绝建表');
      }

      // 尾随逗号
      const bodyNoComments = body.replace(/--.*/g, '').trimEnd();
      if (/,\s*$/.test(bodyNoComments)) {
        errors.push(rel + ': 表 ' + tblName + ' ) 前有尾随逗号 — SQL 语法错误');
      }
    }
  }
  return errors;
}

async function main() {
  const dbHost = process.env.DB_HOST || 'localhost';
  const dbPort = parseInt(process.env.DB_PORT) || 3306;
  const dbUser = process.env.DB_USER || 'root';
  const dbPassword = process.env.DB_PASSWORD || '';
  const dbName = process.env.DB_NAME || 'testdb';

  const sqlDir = path.join(__dirname, '..', 'database');
  const files = findSqlFiles(sqlDir);
  if (!files.length) { console.log('[init-db] No SQL files in database/'); process.exit(0); }

  // 🛑 第一步：自检所有 SQL 文件（在 DROP DATABASE 之前，不动数据库）
  const sorted = files.map(fp => {
    const name = path.basename(fp, '.sql');
    const idx = FK_ORDER.indexOf(name);
    return { path: fp, order: idx === -1 ? 99 : idx };
  }).sort((a, b) => a.order - b.order);

  console.log('[init-db] Pre-flight: validating ' + sorted.length + ' SQL files...');
  const preflightErrors = validateSqlFiles(sorted.map(s => s.path));
  if (preflightErrors.length > 0) {
    console.log('[init-db] ❌ 自检发现 ' + preflightErrors.length + ' 个 SQL 语法错误（数据库未被修改）:');
    preflightErrors.forEach(e => console.log('  ❌ ' + e));
    console.log('[init-db] 请修复以上 SQL 文件后重新运行。');
    process.exit(1);
  }
  console.log('[init-db] ✅ 自检通过');

  // 🛑 第二步：清空旧数据库 + 建新库 + 执行 DDL
  const bootstrap = await mysql.createConnection({ host: dbHost, port: dbPort, user: dbUser, password: dbPassword, multipleStatements: true });
  try {
    await bootstrap.query('DROP DATABASE IF EXISTS `' + dbName + '`');
    await bootstrap.query('CREATE DATABASE `' + dbName + '` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');
    console.log('[init-db] Database `' + dbName + '` recreated (old data cleared)');
  } finally { await bootstrap.end(); }

  const conn = await mysql.createConnection({ host: dbHost, port: dbPort, user: dbUser, password: dbPassword, database: dbName, multipleStatements: true });

  console.log('[init-db] Executing ' + sorted.length + ' SQL files...');
  let ok = 0, fail = 0;
  const failedTables = [];
  for (const { path: fp } of sorted) {
    try {
      const sql = fs.readFileSync(fp, 'utf8');
      await conn.query('SET FOREIGN_KEY_CHECKS=0');
      await conn.query(sql);
      await conn.query('SET FOREIGN_KEY_CHECKS=1');
      console.log('  OK ' + path.basename(fp));
      ok++;
    } catch (e) {
      console.error('  FAIL ' + path.basename(fp) + ': ' + e.message);
      failedTables.push(path.basename(fp));
      fail++;
    }
  }
  await conn.end();

  // 🛑 汇总：打印成功/失败表清单
  console.log('');
  console.log('[init-db] Success:' + ok + ' Failed:' + fail + ' Total:' + (ok + fail));
  if (failedTables.length > 0) {
    console.log('[init-db] ⚠️ 以下 ' + failedTables.length + ' 个表未创建（后续 seed/db_api 测试将受影响）:');
    failedTables.forEach(t => console.log('  ❌ ' + t));
    process.exit(1);
  } else {
    console.log('[init-db] ✅ 全部创建成功');
  }
}

main().catch(e => { console.error('[init-db] Fatal:', e.message); process.exit(1); });
