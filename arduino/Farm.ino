#include <OneWire.h>

OneWire ds(6);
int lamps[3] = {1, 2, 3};
bool lampsOn[3] = {false, false, false};
char vlazh[3] = {A0, A1, A2};
char foto[3] = {A3, A4, A5};
int fan = 4;
bool fanOn = false;
int nasos = 5
bool nasosOn = false;
unsigned int nasosLast = 0, lampsLast[3] = {0, 0, 0};
int nasosDelayOn = 10, lampsDelayOn = 10, nasosDelayOff = 10, lampsDelayOff = 10;
int tempMax = 30;


int fanPower(x)
{
    if(x != fanOn)
    {
        fanOn = !fanOn;
        digitalWrite(fan, fanOn);
    }
    
    return 0;
}

int nasosPower(x)
{
    if(x != nasosOn)
    {
        nasosOn = !nasosOn;
        digitalWrite(nasos, nasosOn);
    }
    
    nasosLast = millis() / 60000
    
    return 0;
}

int lampsPower(x, y)
{
    if(lampsOn[x] != y)
    {
        lampsOn[x] = !lampsOn[x];
        digitalWrite(lamps[x], lampsOn[x]);
    }
    
    lampsLast[x] = millis() / 60000
    
    return 0;
}

int vlPochva(x)
{
    int value = analogRead(vlazh[x-1]);
    value = 1024 - value;
    value = value * 100 / 1024;
    
    return value;    
}

int fotoData(x)
{
    int value = analogRead(foto[x-1]);
    value = 1024 - value;
    value = value * 100 / 1024;
    
    return value;
}

int tempData()
{
    byte temp[2];
    
    ds.reset();
    ds.write(0xCC);
    ds.write(0x44);
    
    delay(1000);
    
    ds.write(0xCC);
    ds.write(0xBE);
    
    data[0] = ds.read();
    data[1] = ds.read();
    
    float temp =  ((data[1] << 8) | data[0]) * 0.0625;
    
    return temp;
}

void setup()
{
    Serial.begin(9600);
    
    for(int i=0; i<3; i++)
    {
        pinMode(vlazh[i], INPUT);
    }
    
    for(int i=0; i<3; i++)
    {
        pinMode(foto[i], INPUT);
    }
    
    for(int i=0; i<3; i++)
    {
        pinMode(lamps[i], OUTPUT);
    }
    
    pinMode(fan, OUTPUT);
}

void loop()
{
    if(nasosOn == true)
    {
        if(millis()/60000 - nasosLast > nasosDelayOn)
        {
            nasosPower(0);
        }
    }
    
    else if(nasosOn == false)
    {
        if(millis()/60000 - nasosLast > nasosDelayOff)
        {
            nasosPower(1);
        }
    }
    
    for(int i=0; i<3; i++)
    {
        if(lampsOn[i] == true)
        {
            if(millis()/60000 - lampslast[i] > lampsDelayOn)
            {
                lampsPower(i, 0);
            }
        }
        
        if(lampsOn[i] == false)
        {
            if(millis()/60000 - lampslast[i] > lampsDelayOff)
            {
                lampsPower(i, 1);
            }
        }        
    }
    
    if(tempData() >= tempMax)
    {
        fanPower(1);
    }
    
    else if(tempData < tempMax)
    {
        fanPower(0);
    }
    
    if(Serial.available())
    {
        String data = Serial.readString();        
    }
    
    if(data[0] == 'I')
    {
        if(data[1] == 'L')
        {
            Serial.println(lampsPower(data[2], data[3]));
        }
        
        else if(data[1] == 'F')
        {
            Serial.println(fanPower(data[2]));
        }
        
        else if(data[1] == 'N')
        {
            Serial.println(nasosPower(data[2]));
        }
        
        else
        {
            Serial.println("Error");
        }
    }
    
    else if(data[0] == 'O')
    {
        if(data[1] == 'L')
        {
            Serial.println(lampsOn[data[2]-1]);
        }
        
        else if(data[1] == 'F')
        {
            Serial.println(fanOn);
        }
        
        else if(data[1] == 'N')
        {
            Serial.println(nasosOn);
        }
        
        else if(data[1] == 'V')
        {
            Serial.println(vlPochva([data[2]-1]));
        }
        
        else if(data[1] == 'O')
        {
            Serial.println(fotoData([data[2]-1]));
        }
        
        else if(data[1] == 'T')
        {
            Serial.println(tempData());
        }
        
        else
        {
            Serial.println("Error");
        }
    }
    
    else
    {
        Serial.println("Error");
    }
}
