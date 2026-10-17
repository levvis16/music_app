CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Wpedantic -O2
TARGET = lab3

.PHONY: all clean check

all: $(TARGET)

$(TARGET): main.cpp
	$(CXX) $(CXXFLAGS) -o $(TARGET) main.cpp

check: $(TARGET)
	./$(TARGET) --self-check

clean:
	rm -f $(TARGET)
