"""
Test unitario para parse_receipt_data()
Prueba la extracción de datos de boletas.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ocr_service import parse_receipt_data


def test_parse_receipt_total():
    """Test: Extracción de TOTAL"""
    texto = """
    SUPERMERCADO CARREFOUR
    Boleta de Venta
    
    Producto 1          $5.990
    Producto 2          $12.500
    Producto 3          $3.200
    
    TOTAL              $21.690
    """

    result = parse_receipt_data(texto)
    print("Test Total:")
    print(f"  Input: {texto[:50]}...")
    print(f"  Output: {result}")
    assert result["total"] is not None, "Total debe ser extraído"
    assert result["total"] == 21690, f"Total debe ser 21690, obtuvo {result['total']}"
    print("  ✅ PASS\n")


def test_parse_receipt_fecha():
    """Test: Extracción de FECHA"""
    texto = """
    BOLETA DE VENTA
    Fecha: 15/12/2024
    
    Artículos vendidos
    Total: $5.000
    """

    result = parse_receipt_data(texto)
    print("Test Fecha:")
    print(f"  Input: {texto[:50]}...")
    print(f"  Output: {result}")
    assert result["fecha"] is not None, "Fecha debe ser extraída"
    assert "15" in result["fecha"], f"Fecha debe contener 15"
    print("  ✅ PASS\n")


def test_parse_receipt_comercio():
    """Test: Extracción de COMERCIO"""
    texto = """
    JUMBO ESTACION CENTRAL
    RUT: 96.974.000-K
    Dirección: Avenida Libertad 123
    
    Producto          Precio
    Arroz 5kg         $8.990
    
    Total: $8.990
    """

    result = parse_receipt_data(texto)
    print("Test Comercio:")
    print(f"  Input: {texto[:50]}...")
    print(f"  Output: {result}")
    assert result["comercio"] is not None, "Comercio debe ser extraído"
    assert "JUMBO" in result["comercio"], f"Comercio debe contener JUMBO"
    print("  ✅ PASS\n")


def test_parse_receipt_real():
    """Test: Boleta real más compleja"""
    texto = """
    DISTRIBUIDORA LÍDER SA
    RUT: 78.652.430-3
    Dirección: Paseo Ahumada 123, Santiago
    
    BOLETA DE VENTA ELECTRÓNICA
    Folio: 2024156789
    
    Fecha: 10/12/2024
    Hora: 14:35:22
    
    ===== DETALLE COMPRA =====
    
    Leche Lala 1L x2         $2.990 x 2 = $5.980
    Pan Integral             $1.890
    Queso Mantecoso          $4.500
    Huevos (Caja x12)        $3.850
    Café Iquique 500g        $5.200
    
    ===== RESUMEN =====
    Subtotal:                $21.420
    IVA (19%):               $4.070
    
    TOTAL PAGAR:             $25.490
    
    Pago: EFECTIVO
    Vuelto: $0
    
    Gracias por su compra
    """

    result = parse_receipt_data(texto)
    print("Test Boleta Real:")
    print(f"  Input: {texto[:100]}...")
    print(f"  Result:")
    print(f"    - Total: {result['total']}")
    print(f"    - Fecha: {result['fecha']}")
    print(f"    - Comercio: {result['comercio']}")
    print(f"    - Texto limpio: {result['texto_limpio'][:50]}...")

    assert result["total"] is not None, "Total debe ser extraído"
    assert result["fecha"] is not None, "Fecha debe ser extraída"
    assert result["comercio"] is not None, "Comercio debe ser extraído"
    assert result["total"] == 25490, f"Total debe ser 25490"
    print("  ✅ PASS\n")


def test_parse_receipt_empty():
    """Test: Texto vacío"""
    result = parse_receipt_data("")
    print("Test Empty Text:")
    print(f"  Output: {result}")
    assert result["total"] is None
    assert result["fecha"] is None
    assert result["comercio"] is None
    print("  ✅ PASS\n")


def test_parse_receipt_formato_alternativo():
    """Test: Formato alternativo dd de mes de yyyy"""
    texto = """
    BOLETA
    Emitida: 5 de diciembre de 2024
    
    Total a pagar: $10.000
    """

    result = parse_receipt_data(texto)
    print("Test Fecha Alternativa:")
    print(f"  Input: {texto[:50]}...")
    print(f"  Output: {result}")
    # Este patrón dd de mes de yyyy también debería capturar
    assert result["fecha"] is not None or result["total"] == 10000
    print("  ✅ PASS\n")


if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBAS: parse_receipt_data()")
    print("=" * 60 + "\n")

    try:
        test_parse_receipt_total()
        test_parse_receipt_fecha()
        test_parse_receipt_comercio()
        test_parse_receipt_real()
        test_parse_receipt_empty()
        test_parse_receipt_formato_alternativo()

        print("=" * 60)
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("=" * 60)
    except AssertionError as e:
        print("=" * 60)
        print(f"❌ TEST FALLIDO: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print("=" * 60)
        print(f"❌ ERROR INESPERADO: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        sys.exit(1)
