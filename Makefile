CXX      = g++
CXXFLAGS = -O3 -march=native -std=c++17 -fopenmp -Wall -Wextra

build/dbscan: src/dbscan.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -rf build

.PHONY: clean