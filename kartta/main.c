#include <conio.h>
#include "kartta.h"

int main(void)
{
    kartta_nayta();
    cgetc();            /* odota näppäintä */
    return 0;
}
