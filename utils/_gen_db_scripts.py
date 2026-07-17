"""Python 自动生成 init-db.js + seed-users.js，由 _ensure_db_scripts 调用。"""
import json
import re
from pathlib import Path

def _validate_sql_files(schema_dir: Path) -> list:
    """预检所有 SQL 文件，发现常见 LLM 生成错误。返回问题列表，为空表示通过。"""
    issues = []

    for fp in sorted(schema_dir.glob("*.sql")):
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception as e:
            issues.append(f"{fp.name}: 无法读取 — {e}")
            continue

        rel = fp.name

        # 1. 括号配对
        depth = 0
        for i, ch in enumerate(content):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth < 0:
                line_no = content[:i].count('\n') + 1
                issues.append(f"{rel}:{line_no}: 多余的 ')' — 括号不配对")
                depth = 0
        if depth > 0:
            issues.append(f"{rel}: 括号未闭合（多了 {depth} 个 '('）")

        # 2. 每个 CREATE TABLE 语句内部检查
        for tm in re.finditer(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE[^;]*',
            content, re.IGNORECASE | re.DOTALL
        ):
            tbl_name = tm.group(1)
            body = tm.group(2)

            # 2a. 重复索引/键名
            idx_names = []
            for im in re.finditer(
                r'(?:UNIQUE\s+)?(?:KEY|INDEX)\s+`(\w+)`',
                body, re.IGNORECASE
            ):
                idx_names.append(im.group(1))
            for im in re.finditer(r'CONSTRAINT\s+`(\w+)`', body, re.IGNORECASE):
                idx_names.append(im.group(1))
            seen = set()
            for name in idx_names:
                if name in seen:
                    issues.append(f"{rel}: 表 `{tbl_name}` 重复索引/约束名 `{name}` — MySQL 会拒绝建表")
                seen.add(name)

            # 2b. 重复列名
            col_names = re.findall(r'`(\w+)`\s+\w+', body)
            col_seen = set()
            for cn in col_names:
                if cn in col_seen:
                    issues.append(f"{rel}: 表 `{tbl_name}` 重复列名 `{cn}`")
                col_seen.add(cn)

            # 2c. 🆕 AUTO_INCREMENT 列必须有 PRIMARY KEY（或 UNIQUE KEY）
            has_auto = bool(re.search(r'AUTO_INCREMENT', body, re.IGNORECASE))
            has_pk = bool(re.search(r'PRIMARY\s+KEY', body, re.IGNORECASE))
            if has_auto and not has_pk:
                issues.append(f"{rel}: 表 `{tbl_name}` AUTO_INCREMENT 列缺少 PRIMARY KEY — MySQL 拒绝建表")

            # 2d. 🆕 尾随逗号（CONSTRAINT 等最后一项后面不能有逗号）
            body_stripped = re.sub(r'--.*', '', body)  # 去掉行注释
            if re.search(r',\s*$', body_stripped.strip()):
                issues.append(f"{rel}: 表 `{tbl_name}` ) 前有尾随逗号 — SQL 语法错误")

            # 2e. 末尾分号检查（匹配文本不含分号，检查紧随其后的字符）
            stmt_end = tm.end()
            if stmt_end >= len(content) or content[stmt_end] not in (';', '；'):
                issues.append(f"{rel}: 表 `{tbl_name}` CREATE TABLE 末尾缺分号")

        # 3. 关键字拼写
        for pattern, correct in [
            (r'\bAUTO_INCREAMENT\b', 'AUTO_INCREMENT'),
            (r'\bPRIAMRY\b', 'PRIMARY'),
            (r'\bFORIEGN\b', 'FOREIGN'),
            (r'\bREFERECNES\b', 'REFERENCES'),
            (r'\bVACHAR\b', 'VARCHAR'),
        ]:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                line_no = content[:m.start()].count('\n') + 1
                issues.append(f"{rel}:{line_no}: 疑似拼写错误 '{m.group(0)}' → 应为 '{correct}'")

    return issues


def generate(ws_path: str, fk_order: str):
    scripts_dir = Path(ws_path) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # 🛑 创建前删除旧脚本，防止残留污染
    for old_file in ["init-db.js", "seed-users.js"]:
        old_path = scripts_dir / old_file
        if old_path.exists():
            old_path.unlink()
            print(f"[_gen_db_scripts] Deleted old {old_file}")

    # 🛑 SQL 预检：生成前扫描全部 DDL 文件，发现错误立即报告
    schema_dir = Path(ws_path) / "database" / "schema"
    if schema_dir.exists():
        sql_issues = _validate_sql_files(schema_dir)
        if sql_issues:
            print(f"[_gen_db_scripts] [WARN] SQL pre-check found {len(sql_issues)} issues (fix before running init-db.js):")
            for issue in sql_issues:
                print(f"  ❌ {issue}")
        else:
            print(f"[_gen_db_scripts] [OK] SQL pre-check passed ({len(list(schema_dir.glob('*.sql')))} files)")

    # init-db.js: 先 DROP DATABASE 清空残留 → 再 CREATE DATABASE → DDL
    (scripts_dir / "init-db.js").write_text("""// scripts/init-db.js - Python auto-generated
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

const FK_ORDER = """ + fk_order + """;

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
    const ctRegex = /CREATE\\s+TABLE\\s+(?:IF\\s+NOT\\s+EXISTS\\s+)?`?(\\w+)`?\\s*\\(([\\s\\S]*?)\\)\\s*ENGINE/gi;
    let ctm;
    while ((ctm = ctRegex.exec(content)) !== null) {
      const tblName = ctm[1];
      const body = ctm[2];

      // 重复索引/约束名
      const idxNames = [];
      const idxRegex = /(?:UNIQUE\\s+)?(?:KEY|INDEX)\\s+`(\\w+)`/gi;
      let im;
      while ((im = idxRegex.exec(body)) !== null) idxNames.push(im[1]);
      const conRegex = /CONSTRAINT\\s+`(\\w+)`/gi;
      while ((im = conRegex.exec(body)) !== null) idxNames.push(im[1]);
      const seenIdx = new Set();
      for (const n of idxNames) {
        if (seenIdx.has(n)) errors.push(rel + ': 表 ' + tblName + ' 重复索引/约束名 `' + n + '` — MySQL 会拒绝建表');
        seenIdx.add(n);
      }

      // 重复列名
      const colNames = [];
      const colRegex = /`(\\w+)`\\s+\\w+/gi;
      let cm;
      while ((cm = colRegex.exec(body)) !== null) colNames.push(cm[1]);
      const seenCol = new Set();
      for (const cn of colNames) {
        if (seenCol.has(cn)) errors.push(rel + ': 表 ' + tblName + ' 重复列名 `' + cn + '`');
        seenCol.add(cn);
      }

      // AUTO_INCREMENT 列必须有 PRIMARY KEY
      if (/AUTO_INCREMENT/i.test(body) && !/PRIMARY\\s+KEY/i.test(body)) {
        errors.push(rel + ': 表 ' + tblName + ' AUTO_INCREMENT 列缺少 PRIMARY KEY — MySQL 会拒绝建表');
      }

      // 尾随逗号
      const bodyNoComments = body.replace(/--.*/g, '').trimEnd();
      if (/,\\s*$/.test(bodyNoComments)) {
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
""", encoding='utf-8')

    # seed-users.js: 仅种子数据
    (scripts_dir / "seed-users.js").write_text("""// scripts/seed-users.js - Python auto-generated
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const bcrypt = require('bcryptjs');

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'your_encryption_key_32chars';
const FK_ORDER = """ + fk_order + """;

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
        const escapedKey = ENCRYPTION_KEY.replace(/'/g, "\\\\'");
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
""", encoding='utf-8')

if __name__ == "__main__":
    import sys
    generate(sys.argv[1], sys.argv[2])
    print("Scripts generated")
