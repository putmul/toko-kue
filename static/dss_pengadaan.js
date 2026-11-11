document.addEventListener('DOMContentLoaded', function () {
    const product = document.getElementById('produk_id');
    const branch = document.getElementById('cabang_id');
    const warehouseStock = document.getElementById('dss-stok-gudang');
    const branchStock = document.getElementById('dss-stok-cabang');
    const minimumStock = document.getElementById('dss-stok-minimum');
    const branchLabel = document.getElementById('dss-stok-cabang-label');

    if (!product || !branch) return;

    function resetStock() {
        warehouseStock.textContent = '-';
        branchStock.textContent = '-';
        minimumStock.textContent = '-';
    }

    function loadStock() {
        if (!product.value) {
            resetStock();
            return;
        }
        const query = branch.value ? '?cabang_id=' + encodeURIComponent(branch.value) : '';
        fetch('/api/dss/stok/' + encodeURIComponent(product.value) + query)
            .then(function (response) {
                if (!response.ok) throw new Error('Gagal mengambil stok');
                return response.json();
            })
            .then(function (data) {
                warehouseStock.textContent = data.stok_gudang + ' unit';
                branchStock.textContent = data.stok_cabang + ' unit';
                minimumStock.textContent = data.stok_minimum + ' unit';
                branchLabel.textContent = branch.value ? 'Cabang yang dipilih' : 'Total cabang aktif';
            })
            .catch(resetStock);
    }

    product.addEventListener('change', loadStock);
    branch.addEventListener('change', loadStock);
    loadStock();
});
