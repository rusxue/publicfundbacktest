/**
 * 文件导出工具：CSV（纯前端，utf-8 BOM 兼容 Excel 中文）。
 * Excel 导出基于同名 .csv + BOM，Excel 可直接识别；如需 .xlsx 真二进制另行扩展。
 */

/** 触发浏览器下载指定内容的文件 */
function download(filename: string, content: string, mime = 'text/csv;charset=utf-8') {
  // 加 BOM，确保 Excel 打开中文不乱码
  const blob = new Blob(['﻿' + content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** 将二维数组导出为 CSV */
export function exportCSV(filename: string, rows: (string | number | null)[][]) {
  const escape = (v: string | number | null) => {
    if (v == null) return ''
    const s = String(v)
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
    return s
  }
  const csv = rows.map((r) => r.map(escape).join(',')).join('\n')
  download(filename.endsWith('.csv') ? filename : `${filename}.csv`, csv)
}

/** Excel 导出：当前以 CSV+BOM 实现（Excel 可识别），文件扩展名 .csv */
export function exportExcel(filename: string, rows: (string | number | null)[][]) {
  exportCSV(filename, rows)
}
