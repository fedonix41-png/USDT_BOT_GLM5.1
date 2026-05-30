import React, { useMemo } from "react";

interface QrProps {
  value: string;
  size?: number;
}

export default function QrCodeGenerator({ value, size = 160 }: QrProps) {
  const matrix = useMemo(() => {
    const dimension = 21;
    const grid = Array(dimension).fill(null).map(() => Array(dimension).fill(false));

    let hash = 0;
    for (let i = 0; i < value.length; i++) {
      hash = (hash << 5) - hash + value.charCodeAt(i);
      hash |= 0;
    }

    const drawEye = (x: number, y: number) => {
      for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 7; c++) {
          const isBorder = r === 0 || r === 6 || c === 0 || c === 6;
          const isCenter = r >= 2 && r <= 4 && c >= 2 && c <= 4;
          if (isBorder || isCenter) {
            grid[y + r][x + c] = true;
          }
        }
      }
    };

    drawEye(0, 0);
    drawEye(dimension - 7, 0);
    drawEye(0, dimension - 7);

    let index = 0;
    for (let r = 0; r < dimension; r++) {
      for (let c = 0; c < dimension; c++) {
        const isTopLeftEye = r < 8 && c < 8;
        const isTopRightEye = r < 8 && c >= dimension - 8;
        const isBottomLeftEye = r >= dimension - 8 && c < 8;
        
        if (!isTopLeftEye && !isTopRightEye && !isBottomLeftEye) {
          const charCode = value.charCodeAt(index % value.length) || 101;
          const shift = (index + hash) % 31;
          const bit = (charCode >> (shift % 8)) & 1;
          grid[r][c] = bit === 1 || (r * c) % 5 === 0;
          index++;
        }
      }
    }

    return { grid, dimension };
  }, [value]);

  const { grid, dimension } = matrix;
  const cellSize = size / dimension;

  return (
    <div className="relative p-3 bg-white rounded-2xl flex items-center justify-center shadow-lg shadow-[#00D09E]/5" style={{ width: size + 24, height: size + 24 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="text-[#0B0E14]">
        {grid.map((row, r) =>
          row.map((active, c) => {
            if (!active) return null;
            return (
              <rect
                key={`${r}-${c}`}
                x={c * cellSize}
                y={r * cellSize}
                width={cellSize - 0.25}
                height={cellSize - 0.25}
                rx={cellSize * 0.18}
                fill="#0B0E14"
              />
            );
          })
        )}
      </svg>
      <div className="absolute w-8 h-8 rounded-lg bg-[#00D09E] border-2 border-white flex items-center justify-center shadow-md">
        <span className="text-[11px] font-black text-white tracking-widest">₮</span>
      </div>
    </div>
  );
}
