// DBSCAN para detección de ruido: versión serial y dos versiones paralelas (OpenMP).
//
// Uso:
//   build/dbscan <entrada.csv> <serial|franjas|malla> [k] [hilos]   -> escribe <N>_results.csv
//   build/dbscan --bench <carpeta_data> <salida.csv>                 -> experimento completo

#include <omp.h>

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

// ---------------------------------------------------------------- parámetros
constexpr double EPS = 0.03;
constexpr double EPS2 = EPS * EPS;           // se compara d² <= ε², equivalente a d <= ε
constexpr double MARGEN = EPS + 1e-9;        // ancho del halo (con holgura numérica)
constexpr int MIN_SAMPLES = 10;              // cuenta el propio punto (igual que sklearn)

enum Etiqueta : unsigned char { RUIDO = 0, CORE = 1, CORE_2 = 2 };
enum class Version { Serial, Franjas, Malla };

struct Puntos {
    std::vector<double> x, y;
    int n() const { return static_cast<int>(x.size()); }
};

// Un subconjunto de puntos: los primeros n_propios son de la región, el resto es su halo.
struct Region {
    std::vector<double> x, y;
    std::vector<int> id;                     // índice global de cada punto
    int n_propios = 0;
};

// ------------------------------------------------------------------- kernels
// Fase 1: un punto propio es core si tiene >= MIN_SAMPLES puntos a distancia <= ε.
static void marcar_cores(const Region& r, std::vector<char>& es_core) {
    const int m = static_cast<int>(r.id.size());
    for (int i = 0; i < r.n_propios; ++i) {
        int vecinos = 0;
        for (int j = 0; j < m && vecinos < MIN_SAMPLES; ++j) {
            const double dx = r.x[i] - r.x[j], dy = r.y[i] - r.y[j];
            vecinos += (dx * dx + dy * dy <= EPS2);
        }
        es_core[r.id[i]] = (vecinos >= MIN_SAMPLES);
    }
}

// Fase 2: un punto no core es core de 2.º orden si tiene un core a distancia <= ε; si no, es ruido.
static void etiquetar(const Region& r, const std::vector<char>& es_core,
                      std::vector<unsigned char>& etiqueta) {
    const int m = static_cast<int>(r.id.size());
    for (int i = 0; i < r.n_propios; ++i) {
        const int g = r.id[i];
        if (es_core[g]) { etiqueta[g] = CORE; continue; }
        etiqueta[g] = RUIDO;
        for (int j = 0; j < m; ++j) {
            const double dx = r.x[i] - r.x[j], dy = r.y[i] - r.y[j];
            if (dx * dx + dy * dy <= EPS2 && es_core[r.id[j]]) { etiqueta[g] = CORE_2; break; }
        }
    }
}

// -------------------------------------------------------------------- serial
// P1: toda la matriz es una sola región indivisible.
static std::vector<unsigned char> dbscan_serial(const Puntos& p) {
    Region todo{p.x, p.y, std::vector<int>(p.n()), p.n()};
    std::iota(todo.id.begin(), todo.id.end(), 0);
    std::vector<char> es_core(p.n());
    std::vector<unsigned char> etiqueta(p.n());
    marcar_cores(todo, es_core);
    etiquetar(todo, es_core, etiqueta);
    return etiqueta;
}

// ------------------------------------------------------------------ paralelo
// El plano se divide en una malla de gx × gy regiones. Cada región toma sus puntos
// más un halo de ancho ε, así el conteo de vecinos de cada punto es exacto.
struct Malla {
    int gx, gy;
    double xmin, ymin, ancho, alto;          // origen y tamaño de cada celda
    int celda_de(double x, double y) const {
        const int cx = std::min(gx - 1, static_cast<int>((x - xmin) / ancho));
        const int cy = std::min(gy - 1, static_cast<int>((y - ymin) / alto));
        return cy * gx + cx;
    }
};

static Malla crear_malla(const Puntos& p, int gx, int gy) {
    const auto [xa, xb] = std::minmax_element(p.x.begin(), p.x.end());
    const auto [ya, yb] = std::minmax_element(p.y.begin(), p.y.end());
    return {gx, gy, *xa, *ya, std::max((*xb - *xa) / gx, 1e-12), std::max((*yb - *ya) / gy, 1e-12)};
}

// Puntos de la celda c más los de otras celdas a distancia <= ε de su rectángulo.
static Region construir_region(const Puntos& p, const std::vector<int>& celda, const Malla& m, int c) {
    const double x0 = m.xmin + (c % m.gx) * m.ancho, x1 = x0 + m.ancho;
    const double y0 = m.ymin + (c / m.gx) * m.alto,  y1 = y0 + m.alto;
    Region r;
    std::vector<int> halo;
    for (int i = 0; i < p.n(); ++i) {
        if (celda[i] == c) { r.id.push_back(i); continue; }
        const double dx = std::max({x0 - p.x[i], 0.0, p.x[i] - x1});
        const double dy = std::max({y0 - p.y[i], 0.0, p.y[i] - y1});
        if (dx * dx + dy * dy <= MARGEN * MARGEN) halo.push_back(i);
    }
    r.n_propios = static_cast<int>(r.id.size());
    r.id.insert(r.id.end(), halo.begin(), halo.end());
    for (int g : r.id) { r.x.push_back(p.x[g]); r.y.push_back(p.y[g]); }
    return r;
}

static std::vector<unsigned char> dbscan_particionado(const Puntos& p, int gx, int gy) {
    const int k = gx * gy;
    const Malla malla = crear_malla(p, gx, gy);

    std::vector<int> celda(p.n());
    #pragma omp parallel for
    for (int i = 0; i < p.n(); ++i) celda[i] = malla.celda_de(p.x[i], p.y[i]);

    std::vector<Region> regiones(k);
    std::vector<char> es_core(p.n());
    std::vector<unsigned char> etiqueta(p.n());

    // Fase 1 (cada punto tiene un único dueño: no hay escrituras compartidas).
    #pragma omp parallel for schedule(dynamic, 1)
    for (int c = 0; c < k; ++c) {
        regiones[c] = construir_region(p, celda, malla, c);
        marcar_cores(regiones[c], es_core);
    }
    // La barrera implícita garantiza que es_core esté completo antes de la fase 2.
    #pragma omp parallel for schedule(dynamic, 1)
    for (int c = 0; c < k; ++c) etiquetar(regiones[c], es_core, etiqueta);

    return etiqueta;
}

// P2a: k franjas verticales.
static std::vector<unsigned char> dbscan_franjas(const Puntos& p, int k) {
    return dbscan_particionado(p, k, 1);
}

// P2b: k celdas casi cuadradas (k potencia de 2: 2x1, 2x2, 4x2, 4x4, 8x4, 8x8).
static std::vector<unsigned char> dbscan_malla(const Puntos& p, int k) {
    int gx = 1;
    while (gx * gx < k) gx *= 2;
    return dbscan_particionado(p, gx, k / gx);
}

static std::vector<unsigned char> ejecutar(Version v, const Puntos& p, int k) {
    switch (v) {
        case Version::Franjas: return dbscan_franjas(p, k);
        case Version::Malla:   return dbscan_malla(p, k);
        default:               return dbscan_serial(p);
    }
}

// ----------------------------------------------------------------------- E/S
static Puntos leer_csv(const std::string& ruta) {
    std::ifstream f(ruta);
    if (!f) { std::cerr << "No se pudo abrir " << ruta << "\n"; std::exit(1); }
    Puntos p;
    std::string linea;
    double a, b;
    while (std::getline(f, linea))
        if (std::sscanf(linea.c_str(), "%lf,%lf", &a, &b) == 2) { p.x.push_back(a); p.y.push_back(b); }
    return p;
}

// <N>_data.csv -> <N>_results.csv (formato que lee DBSCAN_noise.ipynb: x,y,etiqueta)
static void escribir_resultados(const std::string& entrada, const Puntos& p,
                                const std::vector<unsigned char>& etiqueta) {
    const std::string sufijo = "_data.csv";
    std::string salida = entrada;
    if (salida.size() >= sufijo.size() &&
        salida.compare(salida.size() - sufijo.size(), sufijo.size(), sufijo) == 0)
        salida.resize(salida.size() - sufijo.size());
    salida += "_results.csv";
    std::ofstream f(salida);
    for (int i = 0; i < p.n(); ++i) {
        char fila[64];
        std::snprintf(fila, sizeof fila, "%.3f,%.3f,%d\n", p.x[i], p.y[i], etiqueta[i]);
        f << fila;
    }
    std::cout << "Resultados en " << salida << "\n";
}

// ----------------------------------------------------------------- experimento
static int bench(const std::string& carpeta, const std::string& salida) {
    const std::vector<int> tamanos = {20000, 40000, 80000, 120000, 140000, 160000, 180000, 200000};
    const std::vector<int> ks = {2, 4, 8, 16, 32, 64};
    const int repeticiones = 10;
    const int c = omp_get_num_procs();       // cores virtuales
    std::vector<int> hilos = {1, c / 2, c, 2 * c};
    hilos.erase(std::remove(hilos.begin(), hilos.end(), 0), hilos.end());
    hilos.erase(std::unique(hilos.begin(), hilos.end()), hilos.end());

    std::ofstream out(salida);
    out << "version,k,n,hilos,iteracion,tiempo_s,n_ruido\n";
    const std::pair<const char*, Version> versiones[] = {{"franjas", Version::Franjas},
                                                          {"malla", Version::Malla}};
    for (int n : tamanos) {
        const Puntos p = leer_csv(carpeta + "/" + std::to_string(n) + "_data.csv");
        std::cerr << "N = " << n << "\n";
        std::vector<unsigned char> referencia;

        auto medir = [&](const char* nombre, Version v, int k, int h) {
            omp_set_num_threads(h);
            for (int it = 0; it < repeticiones; ++it) {
                const double t0 = omp_get_wtime();
                const auto etiqueta = ejecutar(v, p, k);
                const double dt = omp_get_wtime() - t0;
                if (referencia.empty()) referencia = etiqueta;           // primera corrida serial
                if (etiqueta != referencia) { std::cerr << "ERROR: resultado distinto al serial\n"; std::exit(1); }
                const long ruido = std::count(etiqueta.begin(), etiqueta.end(), RUIDO);
                out << nombre << ',' << k << ',' << n << ',' << h << ',' << it << ',' << dt << ',' << ruido << '\n';
            }
            out.flush();
        };

        medir("serial", Version::Serial, 1, 1);
        for (const auto& [nombre, v] : versiones)
            for (int k : ks)
                for (int h : hilos) medir(nombre, v, k, h);
    }
    return 0;
}

// ------------------------------------------------------------------------ main
int main(int argc, char** argv) {
    if (argc == 4 && std::string(argv[1]) == "--bench") return bench(argv[2], argv[3]);
    if (argc < 3) {
        std::cerr << "Uso: " << argv[0] << " <entrada.csv> <serial|franjas|malla> [k] [hilos]\n"
                  << "     " << argv[0] << " --bench <carpeta_data> <salida.csv>\n";
        return 1;
    }
    const std::string v = argv[2];
    const Version version = v == "franjas" ? Version::Franjas : v == "malla" ? Version::Malla : Version::Serial;
    const int k = argc > 3 ? std::stoi(argv[3]) : 4;
    omp_set_num_threads(argc > 4 ? std::stoi(argv[4]) : omp_get_num_procs());

    const Puntos p = leer_csv(argv[1]);
    const double t0 = omp_get_wtime();
    const auto etiqueta = ejecutar(version, p, k);
    std::cout << "Tiempo: " << omp_get_wtime() - t0 << " s\n";
    escribir_resultados(argv[1], p, etiqueta);
    return 0;
}