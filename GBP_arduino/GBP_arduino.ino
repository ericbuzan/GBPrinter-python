#define GBClock 8
#define GBIn 9
#define GBOut 10

#define delayMs 20

uint8_t cmd;
uint8_t resp;

void setupPrinter(int in, int out, int clock) {
  pinMode(in, INPUT);            // set pin to input
  pinMode(out, OUTPUT);
  pinMode(clock, OUTPUT);
  digitalWrite(in, HIGH);        // turn on pullup resistors
  digitalWrite(out, HIGH);       // turn on pullup resistors
}

uint8_t GBSerialIO(uint8_t cmd) {
  uint8_t resp=0;
  for (uint8_t c=0;  c<8;  c++) {

    //write cycle
    digitalWrite(GBClock, 0);
    if((cmd << c) & 0x80){
      digitalWrite(GBOut, 1);
    }
    else{ 
      digitalWrite(GBOut, 0);
    }
    delayMicroseconds(delayMs);

    //read cycle
    digitalWrite(GBClock, 1);
    resp <<= 1;
    if(digitalRead(GBIn))
    {
      resp |= 1;                  
    }
    delayMicroseconds(delayMs);
  }
  delayMicroseconds(delayMs);
  return resp;
}

void setup() {
  setupPrinter(GBIn, GBOut, GBClock);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    cmd = Serial.read();
    resp = GBSerialIO(cmd);
    Serial.write(resp);
  }
}
